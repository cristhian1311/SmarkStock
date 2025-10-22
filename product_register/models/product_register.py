from odoo import models, fields

class ProductRegister(models.Model):
    _name = 'product.register'
    _description = 'Registro de Productos'

    name = fields.Char(string='Nombre del producto', required=True)
    code = fields.Char(string='Código', required=True)
    description = fields.Text(string='Descripción')
    price = fields.Float(string='Precio')
    quantity = fields.Integer(string='Cantidad')
