class Product:

    def __init__(self, codigo, descripcion, precio, empaque, imagen,
                 familia=None, subfamilia=None, padre=None, variante=None):

        self.codigo = codigo
        self.descripcion = descripcion
        self.precio = precio
        self.empaque = empaque
        self.imagen = imagen

        # Normalización ADSI
        self.familia = familia
        self.subfamilia = subfamilia
        self.padre = padre
        self.variante = variante
        self.color = None
        self.modelo_moto = None
        self.descripcion_tecnica = None
        self.descripcion_marketing = None

    def to_dict(self):
        return {
            "codigo": self.codigo,
            "descripcion": self.descripcion,
            "precio": self.precio,
            "empaque": self.empaque,
            "imagen": self.imagen,
            "familia": self.familia,
            "subfamilia": self.subfamilia,
            "padre": self.padre,
            "variante": self.variante,
            "color": self.color,
            "modelo_moto": self.modelo_moto,
            "descripcion_tecnica": self.descripcion_tecnica,
            "descripcion_marketing": self.descripcion_marketing,
        }
