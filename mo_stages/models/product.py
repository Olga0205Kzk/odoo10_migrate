
from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    so_pdf_note = fields.Html('so pdf note',  related='product_tmpl_id.so_pdf_note')

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    so_pdf_note = fields.Html('so pdf note')