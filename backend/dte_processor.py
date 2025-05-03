import xmltodict, re, os
from datetime import datetime
from collections import defaultdict
from xml.etree import ElementTree as ET
from utils.nit_validator import validar_nit

class DTEProcessor:
    def __init__(self, storage_path=None):
        if storage_path is None:
            storage_path = os.path.join(os.path.dirname(__file__), 'storage')
        self.storage_path = storage_path
        os.makedirs(self.storage_path, exist_ok=True)

        self.correlativos = defaultdict(int)
        self.referencias = set()
        self.estadisticas = {}

    def _init_stats_for_fecha(self, fecha):
        if fecha not in self.estadisticas:
            self.estadisticas[fecha] = {
                'facturas_recibidas': 0,
                'errores': {
                    'FORMATO_INVALIDO': 0,
                    'NIT_EMISOR': 0,
                    'NIT_RECEPTOR': 0,
                    'IVA': 0,
                    'TOTAL': 0,
                    'REFERENCIA_DUPLICADA': 0
                },
                'facturas_correctas': 0,
                'emisores': set(),
                'receptores': set(),
                'aprobaciones': [],
                'valor_total': 0.0,
                'valor_sin_iva': 0.0,
                'iva_emitido': defaultdict(float),
                'iva_recibido': defaultdict(float)
            }

    def procesar_solicitud(self, xml_data):
        data = xmltodict.parse(xml_data)
        dtes = data['SOLICITUD_AUTORIZACION'].get('DTE', [])
        if not isinstance(dtes, list):
            dtes = [dtes]

        for d in dtes:
            raw = d.get('TIEMPO', '')
            parte = raw.split(',', 1)[-1].strip()
            match = re.match(r'(\d{2}/\d{2}/\d{4})', parte)
            fecha = match.group(1) if match else datetime.now().strftime('%d/%m/%Y')

            self._init_stats_for_fecha(fecha)
            self._procesar_factura(d, fecha)

        self._guardar_xml()
        return {'status': 'Procesado exitosamente'}

    def _procesar_factura(self, dte, fecha):
        stats = self.estadisticas[fecha]
        stats['facturas_recibidas'] += 1
        errores = []

        campos = ['REFERENCIA', 'NIT_EMISOR', 'NIT_RECEPTOR', 'VALOR', 'IVA', 'TOTAL']
        if not all(campo in dte for campo in campos):
            stats['errores']['FORMATO_INVALIDO'] += 1
            return

        ref = dte['REFERENCIA'].strip()
        em = dte['NIT_EMISOR'].strip()
        rc = dte['NIT_RECEPTOR'].strip()

        # Validación de NIT
        if not validar_nit(em):
            errores.append('NIT_EMISOR')
        if not validar_nit(rc):
            errores.append('NIT_RECEPTOR')

        # Validar IVA y TOTAL
        try:
            valor = float(dte['VALOR'])
            iva_calc = round(valor * 0.12, 2)
            total_calc = round(valor + iva_calc, 2)
            if float(dte['IVA']) != iva_calc:
                errores.append('IVA')
            if float(dte['TOTAL']) != total_calc:
                errores.append('TOTAL')
        except:
            errores.extend(['IVA', 'TOTAL'])

        # Verificar referencia duplicada
        if ref in self.referencias:
            errores.append('REFERENCIA_DUPLICADA')
        else:
            self.referencias.add(ref)

        if errores:
            for e in errores:
                stats['errores'][e] += 1
        else:
            self.correlativos[fecha] += 1
            cod_aprob = f"{datetime.strptime(fecha, '%d/%m/%Y').strftime('%Y%m%d')}{self.correlativos[fecha]:08d}"

            stats['aprobaciones'].append({
                'NIT_EMISOR': em,
                'REFERENCIA': ref,
                'CODIGO_APROBACION': cod_aprob
            })

            stats['facturas_correctas'] += 1
            stats['emisores'].add(em)
            stats['receptores'].add(rc)
            stats['valor_sin_iva'] += valor
            stats['valor_total'] += total_calc
            stats['iva_emitido'][em] += iva_calc
            stats['iva_recibido'][rc] += iva_calc

    def _guardar_xml(self):
        root = ET.Element('LISTAAUTORIZACIONES')
        for fecha in sorted(self.estadisticas, key=lambda f: datetime.strptime(f, '%d/%m/%Y')):
            stats = self.estadisticas[fecha]
            auth = ET.SubElement(root, 'AUTORIZACION')
            ET.SubElement(auth, 'FECHA').text = fecha
            ET.SubElement(auth, 'FACTURAS_RECIBIDAS').text = str(stats['facturas_recibidas'])

            errs = ET.SubElement(auth, 'ERRORES')
            for key in ['FORMATO_INVALIDO', 'NIT_EMISOR', 'NIT_RECEPTOR', 'IVA', 'TOTAL', 'REFERENCIA_DUPLICADA']:
                ET.SubElement(errs, key).text = str(stats['errores'].get(key, 0))

            ET.SubElement(auth, 'FACTURAS_CORRECTAS').text = str(stats['facturas_correctas'])
            ET.SubElement(auth, 'CANTIDAD_EMISORES').text = str(len(stats['emisores']))
            ET.SubElement(auth, 'CANTIDAD_RECEPTORES').text = str(len(stats['receptores']))

            lista = ET.SubElement(auth, 'LISTADO_AUTORIZACIONES')
            for a in stats['aprobaciones']:
                ap = ET.SubElement(lista, 'APROBACION')
                ET.SubElement(ap, 'NIT_EMISOR', ref=a['REFERENCIA']).text = a['NIT_EMISOR']
                ET.SubElement(ap, 'CODIGO_APROBACION').text = a['CODIGO_APROBACION']
            ET.SubElement(lista, 'TOTAL_APROBACIONES').text = str(stats['facturas_correctas'])

        tree = ET.ElementTree(root)
        tree.write(os.path.join(self.storage_path, 'autorizaciones.xml'), encoding='utf-8', xml_declaration=True)

    def reset(self):
        self.correlativos.clear()
        self.referencias.clear()
        self.estadisticas.clear()

    def obtener_estadisticas(self, fecha):
        return self.estadisticas.get(fecha, {})
