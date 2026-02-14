class TableOrBlockSelector:
    """
    Selector inteligente que decide cuál detector usar:

        - OpenCV (tablas marcadas)
        - LayoutParser (tablas sin líneas)
        - Fallback (bloques)
        - Mixto (tabla + bloques)

    También armoniza y fusiona resultados.
    """

    def __init__(self,
                 min_cells_table=4,
                 lp_confidence_threshold=3,
                 fallback_threshold=5):
        self.min_cells_table = min_cells_table
        self.lp_confidence_threshold = lp_confidence_threshold
        self.fallback_threshold = fallback_threshold

    # --------------------------------------------------------
    # Decide si usar OpenCV
    # --------------------------------------------------------
    def is_probably_table_cv(self, cv_cells):
        return len(cv_cells) >= self.min_cells_table

    # --------------------------------------------------------
    # Decide si usar LayoutParser
    # --------------------------------------------------------
    def is_probably_table_lp(self, lp_cells):
        return len(lp_cells) >= self.lp_confidence_threshold

    # --------------------------------------------------------
    # Decide si la página es tipo mosaico (bloques)
    # --------------------------------------------------------
    def is_mosaic(self, blocks):
        """
        Un mosaico suele tener:
            - muchos bloques medianos
            - o bloques grandes alineados
        """
        if len(blocks) >= self.fallback_threshold:
            return True

        # Si hay pocos pero muy grandes, también es mosaico
        for b in blocks:
            if b["w"] > 250 and b["h"] > 200:
                return True

        return False

    # --------------------------------------------------------
    # Selección del modo
    # --------------------------------------------------------
    def select_mode(self, cv_result, lp_result, fb_result):
        cv_cells = cv_result.get("cells", [])
        lp_cells = lp_result.get("cells", [])
        blocks = fb_result.get("blocks", [])

        cv_table = self.is_probably_table_cv(cv_cells)
        lp_table = self.is_probably_table_lp(lp_cells)
        mosaic = self.is_mosaic(blocks)

        # Caso 1: Tabla clara con OpenCV
        if cv_table and not mosaic:
            return "cv_table"

        # Caso 2: Tabla profunda LayoutParser
        if lp_table and not mosaic:
            return "lp_table"

        # Caso 3: Mosaico
        if mosaic:
            return "blocks"

        # Caso 4: Fallback por falta de estructura
        if len(cv_cells) < self.min_cells_table and len(lp_cells) < self.lp_confidence_threshold:
            return "blocks"

        # Caso 5: Si ambos detectores encuentran algo → mixto
        if cv_table and lp_table:
            return "hybrid"

        return "unknown"

    # --------------------------------------------------------
    # Fusionar resultados cuando es mixto
    # --------------------------------------------------------
    def fuse_results(self, cv_cells, lp_cells):
        """
        Combina celdas detectadas por OpenCV y LayoutParser.
        Las fusiona eliminando duplicados por superposición.
        """
        all_cells = cv_cells + lp_cells
        unique = []

        for c in all_cells:
            duplicate = False
            for u in unique:
                if abs(c["x"] - u["x"]) < 15 and abs(c["y"] - u["y"]) < 15:
                    duplicate = True
                    break
            if not duplicate:
                unique.append(c)

        return unique

    # --------------------------------------------------------
    # Método principal
    # --------------------------------------------------------
    def select(self, cv_result, lp_result, fb_result):
        mode = self.select_mode(cv_result, lp_result, fb_result)

        if mode == "cv_table":
            return {
                "mode": "cv",
                "cells": cv_result["cells"]
            }

        if mode == "lp_table":
            return {
                "mode": "lp",
                "cells": lp_result["cells"]
            }

        if mode == "blocks":
            return {
                "mode": "blocks",
                "cells": fb_result["blocks"]
            }

        if mode == "hybrid":
            fused = self.fuse_results(cv_result["cells"], lp_result["cells"])
            return {
                "mode": "hybrid",
                "cells": fused
            }

        # En caso de duda → fallback
        return {
            "mode": "blocks",
            "cells": fb_result["blocks"]
        }
