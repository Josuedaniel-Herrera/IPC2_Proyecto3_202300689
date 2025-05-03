from flask import Flask, request, jsonify, send_file
from dte_processor import DTEProcessor
import xmltodict, re, os
from io import BytesIO
from datetime import datetime

# ReportLab para PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

app = Flask(__name__)

# Carpeta para XML de entrada y autorizaciones
BASE = os.path.dirname(__file__)
app.config['STORAGE_FOLDER'] = os.path.join(BASE, 'storage')
os.makedirs(app.config['STORAGE_FOLDER'], exist_ok=True)

processor = DTEProcessor(storage_path=app.config['STORAGE_FOLDER'])

@app.route('/api/autorizar', methods=['POST'])
def autorizar_dte():
    xml_data = request.data.decode('utf-8')

    # Guardar el XML original
    ts = datetime.now().strftime('%Y%m%d%H%M%S%f')
    with open(os.path.join(app.config['STORAGE_FOLDER'], f'solicitud_{ts}.xml'), 'w', encoding='utf-8') as f:
        f.write(xml_data)

    # Procesar
    resultado = processor.procesar_solicitud(xml_data)

    # Extraer las fechas reales de los TIEMPO para mostrarlas en el frontend
    fechas = []
    try:
        parsed = xmltodict.parse(xml_data)
        dtes = parsed['SOLICITUD_AUTORIZACION'].get('DTE', [])
        if not isinstance(dtes, list):
            dtes = [dtes]
        fechas_set = set()
        for d in dtes:
            raw = d.get('TIEMPO', '')
            parte = raw.split(',', 1)[-1].strip()
            m = re.match(r'(\d{2}/\d{2}/\d{4})', parte)
            if m:
                fechas_set.add(m.group(1))
        fechas = sorted(
            fechas_set,
            key=lambda d: datetime.strptime(d, '%d/%m/%Y')
        )
    except:
        pass

    resultado['fechas'] = fechas
    return jsonify(resultado)

@app.route('/api/reset', methods=['POST'])
def reset_api():
    processor.reset()
    return jsonify({"status": "Estadísticas reiniciadas"})

@app.route('/api/consultar', methods=['GET'])
def consultar_datos():
    fecha = request.args.get('fecha')
    stats = processor.obtener_estadisticas(fecha)
    if not stats:
        return jsonify({})
    return jsonify({
        'facturas_recibidas': stats['facturas_recibidas'],
        'facturas_correctas': stats['facturas_correctas'],
        'emisores':           list(stats['emisores']),
        'receptores':         list(stats['receptores']),
        'errores':            stats['errores']
    })

@app.route('/api/summary_iva', methods=['GET'])
def summary_iva():
    fecha = request.args.get('fecha')
    stats = processor.estadisticas.get(fecha, {})
    if not stats:
        return jsonify({})
    return jsonify({
        'fecha':        fecha,
        'iva_emitido':  dict(stats['iva_emitido']),
        'iva_recibido': dict(stats['iva_recibido'])
    })

@app.route('/api/summary_rango', methods=['GET'])
def summary_rango():
    from datetime import timedelta
    fmt = '%d/%m/%Y'
    fi = request.args.get('fecha_inicio')
    ff = request.args.get('fecha_fin')
    tipo = request.args.get('tipo', 'total')
    try:
        inicio = datetime.strptime(fi, fmt)
        fin    = datetime.strptime(ff, fmt)
    except:
        return jsonify({'error': 'Formato de fecha inválido'}), 400

    datos = []
    curr = inicio
    while curr <= fin:
        s = curr.strftime(fmt)
        st = processor.estadisticas.get(s, {})
        valor = st.get('valor_sin_iva' if tipo=='siniva' else 'valor_total', 0.0)
        datos.append({'fecha': s, 'valor': valor})
        curr += timedelta(days=1)

    return jsonify({'tipo': tipo, 'datos': datos})

@app.route('/api/report_pdf', methods=['GET'])
def report_pdf():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Título
    elements.append(Paragraph("Reporte de Autorizaciones", styles['Title']))
    elements.append(Spacer(1, 12))

    # Para cada fecha, una sección con tablas
    for fecha, st in sorted(processor.estadisticas.items(),
                            key=lambda kv: datetime.strptime(kv[0], '%d/%m/%Y')):
        elements.append(Paragraph(f"Fecha: {fecha}", styles['Heading2']))
        elements.append(Spacer(1, 6))

        # Tabla de totales
        data_tot = [
            ['Facturas recibidas', st['facturas_recibidas']],
            ['Facturas correctas', st['facturas_correctas']],
            ['Emisores distintos', len(st['emisores'])],
            ['Receptores distintos', len(st['receptores'])]
        ]
        tbl_tot = Table(data_tot, colWidths=[200, 100])
        tbl_tot.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ]))
        elements.append(tbl_tot)
        elements.append(Spacer(1, 12))

        # Tabla de errores
        data_err = [['Error', 'Cantidad']]
        for k, v in st['errores'].items():
            data_err.append([k, v])
        tbl_err = Table(data_err, colWidths=[200, 100])
        tbl_err.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ]))
        elements.append(tbl_err)
        elements.append(Spacer(1, 18))

    # Generar PDF
    doc.build(elements)
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name='reporte_autorizaciones.pdf',
        mimetype='application/pdf'
    )

if __name__ == '__main__':
    app.run(port=5000, debug=True)
