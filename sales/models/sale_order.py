from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _name = 'sale.order'
    _description = 'Pedido de Venta (Personalizado)'

    name = fields.Char(string='Referencia', required=True, default='New')
    date = fields.Date(string='Fecha', default=fields.Date.context_today, required=True)
    product_register_id = fields.Many2one('product.register', string='Producto', required=True)
    quantity = fields.Float(string='Cantidad', required=True, default=1.0)
    unit_price = fields.Float(string='Precio Unitario', compute='_compute_unit_price', store=True)
    total_price = fields.Float(string='Precio Total', compute='_compute_total_price', store=True)
    notes = fields.Text(string='Notas')
    state = fields.Selection([('draft', 'Borrador'), ('done', 'Confirmado'), ('cancel', 'Cancelado')], default='draft')

    @api.depends('product_register_id')
    def _compute_unit_price(self):
        for rec in self:
            rec.unit_price = rec.product_register_id.standard_price if rec.product_register_id else 0.0

    @api.depends('quantity', 'unit_price')
    def _compute_total_price(self):
        for rec in self:
            rec.total_price = (rec.quantity or 0.0) * (rec.unit_price or 0.0)

    def action_confirm(self):
        """Confirmar la venta: crear una salida de inventario marcada como venta"""
        InventoryExit = self.env['inventory.exit']
        Movement = self.env['inventory.movement']
        for rec in self:
            _logger.info('sale.order.action_confirm: confirming sale id=%s product=%s qty=%s current_state=%s', rec.id, rec.product_register_id and rec.product_register_id.id, rec.quantity, rec.state)
            
            if rec.state == 'done':
                _logger.info('sale.order.action_confirm: sale id=%s already confirmed, skipping creation', rec.id)
                continue
            
            exit_vals = {
                'date': rec.date,
                'product_register_id': rec.product_register_id.id,
                'quantity': rec.quantity,
                'customer': rec.name,
                'is_sale': True,
            }
            exit_rec = None
            try:
                exit_rec = InventoryExit.sudo().create(exit_vals)
                _logger.info('sale.order.action_confirm: created inventory.exit id=%s for sale id=%s', exit_rec.id, rec.id)
            except Exception as e:
                _logger.exception('sale.order.action_confirm: failed to create inventory.exit for sale id=%s: %s', rec.id, e)
                
            
            if not exit_rec:
                try:
                    mv_vals = {
                        'date': rec.date,
                        'product_register_id': rec.product_register_id.id,
                        'quantity': rec.quantity,
                        'movement_type': 'salida',
                        'is_sale': True,
                        'origin_model': 'sale.order',
                        'origin_id': rec.id,
                    }
                    mv = Movement.sudo().create(mv_vals)
                    _logger.info('sale.order.action_confirm: created fallback inventory.movement id=%s for sale id=%s (exit creation failed)', mv.id, rec.id)
                except Exception as e:
                    _logger.exception('sale.order.action_confirm: failed to create fallback inventory.movement for sale id=%s: %s', rec.id, e)
            
            try:
                rec.with_context(confirm_via_button=True).write({'state': 'done'})
            except Exception:
                rec.state = 'done'
        return True
    def write(self, vals):
        """Prevent direct writings that set state='done' unless they come with
        the special context key `confirm_via_button` (i.e. the confirmation
        button or authorized code). This ensures saving the form keeps the
        record in draft unless the user explicitly confirms via the button.
        """
        
        if vals.get('state') == 'done' and not self.env.context.get('confirm_via_button'):
            vals = dict(vals)
            vals.pop('state', None)
            _logger.info('sale.order.write: prevented direct state change to done for ids=%s', self.ids)

        return super(SaleOrder, self).write(vals)
