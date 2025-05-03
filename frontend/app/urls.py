from django.urls import path
from . import views

urlpatterns = [
    path('', views.cargar_archivo, name='index'),
    path('consultar/', views.consultar_datos, name='consultar'),
    path('summary_iva/', views.summary_iva, name='summary_iva'),
    path('summary_rango/', views.summary_rango, name='summary_rango'),
    path('report_pdf/', views.report_pdf, name='report_pdf'),
    path('help/', views.help_menu, name='help'),
    path('info/', views.student_info, name='student_info'),
    path('doc/', views.program_doc, name='program_doc'),
    path('reset/', views.reset_api, name='reset'),
]
