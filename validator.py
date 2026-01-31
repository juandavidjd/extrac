class Validator:

    def __init__(self):
        pass

    def validate(self, productos):
        """
        Valida productos generando una lista de errores y advertencias.
        Cada producto devuelve una estructura:
        {
            producto: Product,
            errores: [],
            advertencias: []
        }
        """
        report = []

        for p in productos:
            errores = []
            advertencias = []

            # Código inválido
            if not p.codigo or len(str(p.codigo)) < 3:
                errores.append("CODIGO_INVALIDO")

            # Precio inválido
            if p.precio is None:
                advertencias.append("PRECIO_NO_DETECTADO")

            # Empaque roto
            if p.empaque is None:
                advertencias.append("EMPAQUE_NO_DETECTADO")

            # Sin imagen asignada
            if p.imagen is None:
                errores.append("SIN_IMAGEN")

            # Sin familia
            if p.familia is None:
                advertencias.append("FAMILIA_NO_DETECTADA")

            # Descripción vacía
            if p.descripcion is None or len(p.descripcion.strip()) == 0:
                errores.append("DESCRIPCION_VACIA")

            report.append({
                "producto": p,
                "errores": errores,
                "advertencias": advertencias
            })

        return report
