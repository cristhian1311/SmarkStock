from odoo import models, fields, api, _
import base64
import csv
import io
import logging
import zipfile
import re
from urllib import request as urlrequest

_logger = logging.getLogger(__name__)


class ProductRegisterImportWizard(models.TransientModel):
    _name = 'product.register.import.wizard'
    _description = 'Importar Productos desde CSV'

    data_file = fields.Binary(string='Archivo CSV', required=True)
    filename = fields.Char(string='Nombre de archivo')
    delimiter = fields.Selection([(',', 'Comma (,)'), (';', 'PuntoComa (;)')], string='Delimitador', default=',')
    update_existing = fields.Boolean(string='Actualizar existentes (por barcode o nombre)', default=True)
    encoding = fields.Char(string='Encoding', default='utf-8')
    note = fields.Text(string='Resultado', readonly=True)
    images_zip = fields.Binary(string='ZIP de imágenes (opcional)')
    images_zip_filename = fields.Char(string='Nombre ZIP')
    stock_action = fields.Selection([
        ('ignore', 'Ignorar columna de stock'),
        ('adjust', 'Ajustar stock creando movimientos')
    ], string='Acción sobre stock', default='adjust')

    def _normalize_bool(self, value):
        if value is None:
            return False
        v = str(value).strip().lower()
        return v in ('1', 'true', 't', 'si', 'yes', 'y')

    def action_import(self):
        self.ensure_one()
        content = base64.b64decode(self.data_file) if self.data_file else b''
        try:
            text = content.decode(self.encoding or 'utf-8')
        except Exception:
            text = content.decode(self.encoding or 'utf-8', errors='replace')

        
        chosen_delim = self.delimiter or ','
        try:
            sample = '\n'.join(text.splitlines()[:5])
            if not self.delimiter or self.delimiter == ',':
                dialect = csv.Sniffer().sniff(sample)
                chosen_delim = dialect.delimiter
        except Exception:
            first_line = text.splitlines()[0] if text.splitlines() else ''
            if ';' in first_line and chosen_delim == ',':
                chosen_delim = ';'

        
        stream = io.StringIO(text)
        reader = csv.DictReader(stream, delimiter=chosen_delim)

        Product = self.env['product.register'].sudo()
        created = 0
        updated = 0
        movements_created = 0
        errors = []

        
        zip_map = {}
        if self.images_zip:
            try:
                zip_bytes = base64.b64decode(self.images_zip)
                with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                    for name in zf.namelist():
                        fname = name.split('/')[-1]
                        try:
                            zip_map[fname] = zf.read(name)
                        except Exception:
                            _logger.warning('Could not read %s from uploaded zip', name)
            except Exception:
                _logger.exception('Failed to process uploaded images zip')

        for row_idx, row in enumerate(reader, start=1):
            
            data = {k.strip().lower(): (v.strip() if v is not None else '') for k, v in row.items()}

            
            vals = {}
            if 'name' in data and data['name']:
                vals['name'] = data['name']
            else:
                errors.append(_('Row %s: missing name') % row_idx)
                continue

            
            try:
                vals['standard_price'] = float(data.get('standard_price') or 0.0)
            except Exception:
                vals['standard_price'] = 0.0

            if 'barcode' in data and data['barcode']:
                vals['barcode'] = data['barcode']

            if 'expiration_date' in data and data['expiration_date']:
                vals['expiration_date'] = data['expiration_date']

            if 'type' in data and data['type']:
                
                t = data['type'].lower()
                if t in ('product', 'producto', 'producto almacenable', 'producto almacenable'):
                    vals['type'] = 'product'
                elif t in ('service', 'servicio'):
                    vals['type'] = 'service'
                elif t in ('consu', 'consumible'):
                    vals['type'] = 'consu'
                else:
                    # default keep as product
                    vals['type'] = 'product'

            if 'active' in data and data['active']:
                vals['active'] = self._normalize_bool(data['active'])

            
            
            
            
            image_value = None
            for key in ('image_1920', 'image', 'image_url', 'image_filename'):
                if key in data and data[key]:
                    image_value = data[key]
                    break

            def _is_base64(s):
                if s.startswith('data:image/') and 'base64,' in s:
                    return True
                s2 = re.sub(r"^data:image/[^;]+;base64,", "", s)
                if len(s2) < 100:
                    return False
                return re.match(r'^[A-Za-z0-9+/=\n\r]+$', s2) is not None

            def _get_image_bytes_from_value(val):
                
                if not val:
                    return None
                v = val.strip()
                if v.startswith('data:image/') and 'base64,' in v:
                    b64 = v.split('base64,', 1)[1]
                    try:
                        return base64.b64decode(b64)
                    except Exception:
                        return None
                if v.startswith('http://') or v.startswith('https://'):
                    try:
                        with urlrequest.urlopen(v, timeout=10) as resp:
                            return resp.read()
                    except Exception:
                        _logger.warning('Failed to fetch image from URL: %s', v)
                        return None
                if v in zip_map:
                    return zip_map[v]
                if _is_base64(v):
                    try:
                        clean = re.sub(r'\s+', '', v)
                        return base64.b64decode(clean)
                    except Exception:
                        return None
                return None

            if image_value:
                img_bytes = _get_image_bytes_from_value(image_value)
                if img_bytes:
                    try:
                        vals['image_1920'] = base64.b64encode(img_bytes).decode('utf-8')
                    except Exception:
                        vals['image_1920'] = base64.b64encode(img_bytes)

                
            existing = None
            if self.update_existing:
                if vals.get('barcode'):
                    existing = Product.search([('barcode', '=', vals.get('barcode'))], limit=1)
                if not existing:
                    existing = Product.search([('name', '=', vals.get('name'))], limit=1)

            try:
                
                if existing:
                    existing.write(vals)
                    prod_rec = existing
                    updated += 1
                else:
                    prod_rec = Product.create(vals)
                    created += 1

                
                if self.stock_action == 'adjust':
                    
                    desired_stock = None
                    for stock_key in ('stock', 'quantity', 'qty'):
                        if stock_key in data and data[stock_key]:
                            try:
                                desired_stock = float(data[stock_key])
                            except Exception:
                                desired_stock = None
                            break

                    if desired_stock is not None:
                        
                        Movement = self.env['inventory.movement']
                        domain = [('product_register_id', '=', prod_rec.id)]
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
                        current = total_in - total_out
                        delta = desired_stock - current
                        
                        if abs(delta) > 1e-9:
                            mv_vals = {
                                'date': fields.Date.context_today(self),
                                'product_register_id': prod_rec.id,
                                'quantity': abs(delta),
                                'movement_type': 'entrada' if delta > 0 else 'salida',
                                'origin_model': 'product.register.import',
                                'origin_id': self.id,
                            }
                            try:
                                Movement.create(mv_vals)
                                movements_created += 1
                            except Exception as e:
                                _logger.exception('Failed to create stock movement for row %s: %s', row_idx, e)
                                errors.append(_('Row %s (stock): %s') % (row_idx, str(e)))
            except Exception as e:
                _logger.exception('Error importing row %s: %s', row_idx, e)
                errors.append(_('Row %s: %s') % (row_idx, str(e)))

        note_lines = [_('Import finished'), _('Created: %s') % created, _('Updated: %s') % updated, _('Movements created: %s') % movements_created]
        if errors:
            note_lines.append(_('Errors:'))
            note_lines += errors

        self.note = '\n'.join(note_lines)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.register.import.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
