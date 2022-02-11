# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class Project(models.Model):
    _inherit = 'project.project'

    expenses_sum = fields.Float(compute='_compute_expenses_sum')

    def _compute_expenses_sum(self):
        for record in self:
            sum = 0
            if record.analytic_account_id:
                expenses = self.env['hr.expense'].search([('analytic_account_id', '=', record.analytic_account_id.id)])
                for expense in expenses:
                    sum += expense.unit_amount
            record.expenses_sum = sum

    def action_view_expenses(self):
        return  {
            'type': 'ir.actions.act_window',
            'name': _('Expenses'),
            'res_model': 'hr.expense',
            'view_mode': 'tree,form',
            'domain': [('analytic_account_id', '=', self.analytic_account_id.id)],

        }


