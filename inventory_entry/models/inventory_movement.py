from odoo import models, fields, api


class InventoryMovement(models.Model):
    _name = 'inventory.movement'
    _description = 'Movimiento de Inventario (Entradas/Salidas)'
    _order = 'date desc'

    date = fields.Date(string='Fecha', required=True)
    product_register_id = fields.Many2one('product.register', string='Producto', required=True)
    quantity = fields.Float(string='Cantidad', required=True)
    movement_type = fields.Selection([('entrada', 'Entrada'), ('salida', 'Salida')], string='Tipo', required=True)
    origin_model = fields.Char(string='Modelo Origen')
    origin_id = fields.Integer(string='ID Origen')
    is_sale = fields.Boolean(string='Salida por Venta', default=False)

    def name_get(self):
        result = []
        for rec in self:
            name = '%s - %s: %s' % (rec.date or '', rec.product_register_id.name or '', rec.quantity)
            result.append((rec.id, name))
        return result

    @api.model
    def create(self, vals):
        rec = super(InventoryMovement, self).create(vals)
        
        return rec

    def write(self, vals):
        old = {r.id: {'quantity': r.quantity, 'movement_type': r.movement_type, 'product_id': r.product_register_id.id} for r in self}
        res = super(InventoryMovement, self).write(vals)
        for rec in self:
            try:
                old_vals = old.get(rec.id)
                old_qty = old_vals and (old_vals.get('quantity') or 0.0) or 0.0
                old_type = old_vals and old_vals.get('movement_type')
                old_prod_id = old_vals and old_vals.get('product_id')

                new_qty = rec.quantity or 0.0
                new_type = rec.movement_type
                new_prod = rec.product_register_id

                
            except Exception:
                pass
        return res

    def unlink(self):
        return super(InventoryMovement, self).unlink()
