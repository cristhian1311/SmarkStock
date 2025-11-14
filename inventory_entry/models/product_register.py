from odoo import models, fields, api

class InventoryEntry(models.Model):
    _name = 'inventory.entry'
    _description = 'Entrada de Inventario'

    date = fields.Date(string='Fecha', default=fields.Date.today, required=True)
    product_register_id = fields.Many2one('product.register', string='Producto', required=True)
    quantity = fields.Float(string='Cantidad', required=True)
    supplier = fields.Text(string='Proveedor')
    unit_cost = fields.Float(string='Costo Unitario', compute='_compute_unit_cost', store=True)
    total_cost = fields.Float(string='Costo Total', compute='_compute_total_cost', store=True)
    notes = fields.Text(string='Notas')

    @api.depends('product_register_id')
    def _compute_unit_cost(self):
        for record in self:
            if record.product_register_id:
                record.unit_cost = record.product_register_id.standard_price
            else:
                record.unit_cost = 0.0

    @api.depends('quantity', 'unit_cost')
    def _compute_total_cost(self):
        for record in self:
            record.total_cost = record.quantity * record.unit_cost

    def action_create_product_register(self):
        """Abrir formulario personalizado para crear producto"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Crear Producto Personalizado',
            'res_model': 'product.register',
            'view_mode': 'form',
            'target': 'new',
        }

    @api.onchange('product_register_id')
    def _onchange_product_register_id(self):
        """Actualizar campos cuando se selecciona un producto"""
        if self.product_register_id:
            self.unit_cost = self.product_register_id.standard_price

    def create_movement_for(self, rec):
        self.env['inventory.movement'].create({
            'date': rec.date,
            'product_register_id': rec.product_register_id.id,
            'quantity': rec.quantity,
            'movement_type': 'entrada',
            'origin_model': 'inventory.entry',
            'origin_id': rec.id,
        })

    @api.model
    def create(self, vals):
        rec = super(InventoryEntry, self).create(vals)
        try:
            self.create_movement_for(rec)
        except Exception:
            pass
        return rec

    def write(self, vals):
        res = super(InventoryEntry, self).write(vals)
        for rec in self:
            mv = self.env['inventory.movement'].search([('origin_model', '=', 'inventory.entry'), ('origin_id', '=', rec.id)], limit=1)
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
            mv = self.env['inventory.movement'].search([('origin_model', '=', 'inventory.entry'), ('origin_id', '=', rec.id)])
            if mv:
                mv.unlink()
        return super(InventoryEntry, self).unlink()
