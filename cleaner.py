class Cleaner:

    def __init__(self):
        pass

    def fix(self, report):
        """
        Corrige errores comunes basados en el reporte del validador.
        """
        productos_limpios = []

        for entry in report:

            p = entry["producto"]
            errores = entry["errores"]
            advertencias = entry["advertencias"]

            # --- Correcciones automáticas ---

            # si no detectó empaque, intentar extraerlo de descripción
            if "EMPAQUE_NO_DETECTADO" in advertencias:
                if "X" in p.descripcion.upper():
                    for tok in p.descripcion.upper().split():
                        if tok.startswith("X") and len(tok) <= 4:
                            p.empaque = tok

            # si no detectó precio, intentar extraer números grandes
            if "PRECIO_NO_DETECTADO" in advertencias:
                import re
                nums = re.findall(r"\b\d{3,7}\b", p.descripcion)
                if nums:
                    p.precio = max(nums)

            # si no detectó familia, inferirla por claves
            if "FAMILIA_NO_DETECTADA" in advertencias:
                if "CAUCHO" in p.descripcion.upper():
                    p.familia = "CAUCHOS"
                elif "TOOL" in p.descripcion.upper() or "HERR" in p.descripcion.upper():
                    p.familia = "HERRAMIENTAS"
                else:
                    p.familia = "OTROS"

            # si no hay imagen, marcar producto como "IMAGEN_PENDIENTE"
            if "SIN_IMAGEN" in errores:
                p.imagen = "IMAGEN_PENDIENTE"

            productos_limpios.append(p)

        return productos_limpios
