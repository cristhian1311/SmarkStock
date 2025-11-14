from odoo import models, fields, api

class ProductRegister(models.Model):
    _name = 'product.register'
    _description = 'Registro de Producto Personalizado'

    name = fields.Char(string='Nombre del Producto', required=True)
    standard_price = fields.Float(string='Precio Costo', required=True)
    barcode = fields.Char(string='Código de Barras')
    expiration_date = fields.Date(string='Fecha de Caducidad')
    type = fields.Selection([
        ('product', 'Producto Almacenable'),
        ('service', 'Servicio'),
        ('consu', 'Consumible'),
    ], string='Tipo de Producto', default='product', required=True)
    
    image_1920 = fields.Image(string='Imagen del Producto', max_width=1920, max_height=1920)
    image_1024 = fields.Image(related='image_1920', max_width=1024, max_height=1024, store=True)
    image_512 = fields.Image(related='image_1920', max_width=512, max_height=512, store=True)
    image_256 = fields.Image(related='image_1920', max_width=256, max_height=256, store=True)
    image_128 = fields.Image(related='image_1920', max_width=128, max_height=128, store=True)
    
    active = fields.Boolean(string='Activo', default=True)
    quantity = fields.Float(string='Cantidad en Stock', compute='_compute_stock')

    def _compute_stock(self):
        for rec in self:
            Movement = self.env['inventory.movement']
            if 'inventory.movement' in self.env:
                domain = [('product_register_id', '=', rec.id)]
                groups = Movement.read_group(domain, ['movement_type', 'quantity'], ['movement_type'])
                total_in = 0.0
                total_out = 0.0
                for g in groups:
                    mtype = g.get('movement_type')
                    qty = g.get('quantity') or 0.0
                    if mtype == 'entrada':
                        total_in += qty
                    elif mtype == 'salida':
                        total_out += qty
                rec.quantity = total_in - total_out
            else:
                rec.quantity = 0.0
