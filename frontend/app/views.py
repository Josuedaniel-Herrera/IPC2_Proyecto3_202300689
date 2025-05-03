from django.shortcuts import render, redirect
from django.http import HttpResponse
import requests

API_BASE = 'http://localhost:5000/api'

def cargar_archivo(request):
    result = None
    fechas = []
    if request.method == 'POST' and request.FILES.get('archivo'):
        archivo = request.FILES['archivo']
        try:
            resp = requests.post(f'{API_BASE}/autorizar', data=archivo.read())
            data = resp.json()
            if 'error' in data:
                result = data['error']
            else:
                result = data.get('status')
                fechas = data.get('fechas', [])
                if fechas:
                    # redirige automáticamente a Consultar con la primera fecha válida
                    return redirect(f'/consultar/?fecha={fechas[0]}')
        except requests.RequestException as e:
            result = f"Error al conectar con el backend: {e}"
    return render(request, 'index.html', {'result': result, 'fechas': fechas})

def reset_api(request):
    try:
        requests.post(f'{API_BASE}/reset')
    except:
        pass
    return redirect('index')

def consultar_datos(request):
    data = {}
    fecha = request.GET.get('fecha')
    if fecha:
        try:
            resp = requests.get(f'{API_BASE}/consultar', params={'fecha': fecha})
            data = resp.json()
        except requests.RequestException:
            data = {}
    return render(request, 'resultados.html', {'data': data, 'fecha': fecha})

def summary_iva(request):
    chart_data = {}
    fecha = request.GET.get('fecha')
    if fecha:
        try:
            resp = requests.get(f'{API_BASE}/summary_iva', params={'fecha': fecha})
            chart_data = resp.json()
        except requests.RequestException:
            chart_data = {}
    return render(request, 'summary_iva.html', {'chart_data': chart_data, 'fecha': fecha})

def summary_rango(request):
    """
    Ahora pasa fecha_inicio, fecha_fin y tipo al template.
    """
    chart_data = {}
    fi = request.GET.get('fecha_inicio')
    ff = request.GET.get('fecha_fin')
    tipo = request.GET.get('tipo', 'total')
    if fi and ff:
        try:
            resp = requests.get(
                f'{API_BASE}/summary_rango',
                params={'fecha_inicio': fi, 'fecha_fin': ff, 'tipo': tipo}
            )
            chart_data = resp.json()
        except requests.RequestException:
            chart_data = {}
    return render(request, 'summary_rango.html', {
        'chart_data': chart_data,
        'fecha_inicio': fi,
        'fecha_fin': ff,
        'tipo': tipo
    })

def report_pdf(request):
    try:
        resp = requests.get(f'{API_BASE}/report_pdf')
        return HttpResponse(resp.content, content_type='application/pdf')
    except requests.RequestException:
        return HttpResponse("Error al generar PDF.", status=500)

def help_menu(request):
    return render(request, 'help.html')

def student_info(request):
    return render(request, 'student_info.html')

def program_doc(request):
    return render(request, 'program_doc.html')
