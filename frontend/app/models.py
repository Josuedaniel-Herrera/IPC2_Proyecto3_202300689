from django.db import models

# Ejemplo de modelo para estadísticas (opcional)
class Estadistica(models.Model):
    fecha = models.DateField()
    facturas_correctas = models.IntegerField()
    
    def __str__(self):
        return f"Estadísticas del {self.fecha}"