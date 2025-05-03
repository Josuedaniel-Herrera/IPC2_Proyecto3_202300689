def validar_nit(nit):
    if len(nit) < 1 or len(nit) > 20:
        return False
    try:
        verificador = nit[-1].upper()
        cuerpo = nit[:-1]
        suma = 0
        pos = len(cuerpo) + 1

        for c in cuerpo:
            suma += int(c) * pos
            pos -= 1

        mod = suma % 11
        resultado = (11 - mod) % 11

        return (resultado == 10 and verificador == 'K') or (str(resultado) == verificador)
    except:
        return False