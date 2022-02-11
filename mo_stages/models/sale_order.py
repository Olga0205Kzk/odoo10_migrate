
from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    state = fields.Selection([
        ('draft', 'Quotation'),
        ('practice_head_agreed', 'Agreed by the head of practice'),
        ('approval', 'Approval'),
        ('approved', 'Approved'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    so_pdf_note = fields.Html('so pdf note')

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.so_pdf_note = self.product_id.product_tmpl_id.so_pdf_note