from odoo import models, fields, api

class InventoryExit(models.Model):
    _name = 'inventory.exit'
    _description = 'Salida de Inventario'

    date = fields.Date(string='Fecha', default=fields.Date.today, required=True)
    product_register_id = fields.Many2one('product.register', string='Producto', required=True)
    quantity = fields.Float(string='Cantidad', required=True)
    customer = fields.Text(string='Cliente')
    unit_price = fields.Float(string='Precio Unitario', compute='_compute_unit_price', store=True)
    total_price = fields.Float(string='Precio Total', compute='_compute_total_price', store=True)
    notes = fields.Text(string='Notas')
    is_sale = fields.Boolean(string='Salida por Venta', default=False)

    @api.depends('product_register_id')
    def _compute_unit_price(self):
        for record in self:
            if record.product_register_id:
                record.unit_price = record.product_register_id.standard_price
            else:
                record.unit_price = 0.0

    @api.depends('quantity', 'unit_price')
    def _compute_total_price(self):
        for record in self:
            record.total_price = record.quantity * record.unit_price

    def create_movement_for(self, rec):
        vals = {
            'date': rec.date,
            'product_register_id': rec.product_register_id.id,
            'quantity': rec.quantity,
            'movement_type': 'salida',
            'origin_id': rec.id,
        }
        if getattr(rec, 'is_sale', False):
            vals['is_sale'] = True
            vals['origin_model'] = 'sale.order'
        else:
            vals['origin_model'] = 'inventory.exit'
        self.env['inventory.movement'].create(vals)

    @api.model
    def create(self, vals):
        rec = super(InventoryExit, self).create(vals)
        try:
            self.create_movement_for(rec)
        except Exception:
            pass
        return rec

    def write(self, vals):
        res = super(InventoryExit, self).write(vals)
        for rec in self:
            mv = self.env['inventory.movement'].search([('origin_id', '=', rec.id), ('origin_model', 'in', ['inventory.exit', 'sale.order'])], limit=1)
            if mv:
                mv.write({
                    'date': rec.date,
                    'product_register_id': rec.product_register_id.id,
                    'quantity': rec.quantity,
                })
            else:
                try:
                    self.create_movement_for(rec)
                except Exception:
                    pass
        return res

    def unlink(self):
        for rec in self:
            mv = self.env['inventory.movement'].search([('origin_id', '=', rec.id), ('origin_model', 'in', ['inventory.exit', 'sale.order'])])
            if mv:
                mv.unlink()
        return super(InventoryExit, self).unlink()