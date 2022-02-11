from xmlrpc.client import ServerProxy, Error
from odoo import models, fields, api
from datetime import datetime, date
import requests
from odoo.http import request
from string import digits
import logging
from odoo.exceptions import AccessError, UserError
from odoo.tests import Form

_logger = logging.getLogger(__name__)

fields_to_read_crm = [
    'id',
    'name',
    'partner_id',
    'company_id',
    'team_id',
    'state_id',
    'stage_id',
    'user_id',
    'city',
    'contact_name',
    'description',
    'mobile',
    'partner_name',
    'phone',
    'probability',
    'planned_revenue',
    'street',
    'street2',
    'zip',
    'create_date',
    'date_action_last',
    'company_currency',
    'email_from',
    'email_cc',
    'type',
    'order_ids',
    'priority',
    'website']

fields_to_read_sale_order = [
    'id',
    'name',
    'team_id',
    'project_id',
    'amount_total',
    'amount_untaxed',
    'amount_tax',
    'date_order',
    'user_id',
    'sale_partner_id',
    'partner_id',
    'state',
    'company_id',
    'project_project_id',
    'opportunity_id',
    'create_date'

]
fields_to_read_product = [
    'name'
]
fields_to_read_project_task = [
    'project_id'
]

product_10_product_14_names_dict = {
    '2.1. Юридичний аудит об’єкта': '1.2.1 Юридичний аудит об’єкта',
    '5.1. Супровід отримання МБУіО': '1.4.1 Супровід отримання МБУіО',
}

lead_stage = {
    1: 1,  # Встановити зв'язок
    20: 3,  # ЛПР/ЛВР
    3: 3,  # Перемовини 1 етап
    6: 6,  # Аналітика потреб
    4: 5,  # Зустріч з партнером
    21: 5,  # Перемовини 2 етап
    22: 7,  # кп
    18: 1,  # Пауза
    15: 11,  # Пiдписан договiр (впіймано)
    12: 1,  # Компанія "Обзвон інвентаризація"
    16: 16,  # Оплачено
}


def connect():
    url = 'http://168.119.94.235:8069'
    db = 'totum'
    username = 'o.kazakova@totum.com.ua'
    password = '7263542Olga'

    common = ServerProxy('{}/xmlrpc/2/common'.format(url))
    common.version()
    uid = common.authenticate(db, username, password, {})
    models_rpc = ServerProxy('{}/xmlrpc/2/object'.format(url))
    return models_rpc, db, password, uid

def get_partner_name(partner_name):
    if partner_name.startswith('-') or partner_name.startswith(' ') or partner_name[0].isdigit():
        partner_name = partner_name[1:]
        if partner_name.startswith('-') or partner_name.startswith(' ') or partner_name[0].isdigit():
            return get_partner_name(partner_name)
        else:
            return partner_name
    else:
        return partner_name

def sync_data(cntx, lead):
    # order_ids = True
    # if lead['type'] == 'opportunity':
    #     if lead['order_ids'] and len(lead['order_ids']) > 0:
    #         return
    #     else:
    #         order_ids = False
    # del lead['order_ids']
    if 'user_id' in lead and lead['user_id']:
        # user = users.get(lead['user_id'][0], False)
        user = cntx.create_uid.search([('name', '=', lead['user_id'][1])])
        if user:
            lead['user_id'] = user.id
        else:
            lead['user_id'] = 100
    else:
        if lead['user_id'] != False:
            user = cntx.partner_id.search([('name', '=', lead['user_id'][1])])
            if user:
                lead['user_id'] = user.user_id.id
            else:
                lead['user_id'] = 100
        else:
            lead['user_id'] = 100

    if lead['company_id'] and len(lead['company_id']) > 0:
        del lead['company_id']

    if lead['partner_id'] and len(lead['partner_id']) > 0:
        partner_name = get_partner_name(lead['partner_id'][1])
        partner_id = cntx.partner_id.search([('name', '=', partner_name.strip())], limit=1)
        if partner_id:
            lead['partner_id'] = partner_id.id
        else:
            partner_id = cntx.partner_id.search([('name', 'like', partner_name.strip())], limit=1)
            if partner_id:
                lead['partner_id'] = partner_id.id
            else:
                try:
                    if lead['user_id'] != 100:
                        partner_id = user.partner_id.id
                        lead['partner_id'] = partner_id.id
                    else:
                        usr = cntx.create_uid.search([('id', '=', 100)])
                        partner_id = usr.partner_id.id
                        lead['partner_id'] = partner_id.id
                except Exception:
                    del lead['partner_id']


    if lead['team_id'] and len(lead['team_id']) > 0:
        del lead['team_id']

    if lead['type'] != 'opportunity':
        lead['stage_id'] = 1
        lead['type'] = 'opportunity'
    else:
        lead['stage_id'] = 6

    if lead['type'] != 'lead':
        lead['expected_revenue'] = lead['planned_revenue']
        del lead['planned_revenue']
    else:
        del lead['planned_revenue']

    lead['id_lbs_connect'] = lead['id']
    del lead['id']
    create_date = lead['create_date']
    # if 'create_date' in lead:
    #     del lead['create_date']

    # curr_exist = cntx.search_read([('id_lbs_connect', '=', lead['id_lbs_connect'])], fields=fields_to_read_local)
    lead['stage_id'] = 1
    curr_exist = cntx.search([('id_lbs_connect', '=', lead['id_lbs_connect'])])
    try:
        if curr_exist:
            curr_exist.write(lead)
            return

        new_lead = cntx.with_context(exchange=True).create(lead)
        new_lead.sudo().write({
            'date_open': lead['create_date'],
            'team_id': False
        })
        mod_date_empty = cntx.search([('name', '=', 'mod_date_empty')])
        # if lead['type'] == 'opportunity':
        #     if order_ids == False and new_lead:
        #         try:
        #             if partner_id:
        #                 new_lead.order_ids.create({
        #                     'partner_id': partner_id.id if partner_id else False,
        #                     'opportunity_id': new_lead.id,
        #                     'user_id': new_lead.user_id.id,
        #                     'currency_id': new_lead.company_currency.id
        #                 })
        #         except Exception:
        #             pass

        if mod_date_empty:
            if datetime.strptime(mod_date_empty.value_var,
                                 '%Y-%m-%d %H:%M:%S') > datetime.strptime(create_date,
                                                                          '%Y-%m-%d %H:%M:%S'):
                return
    except Exception as error:
        pass


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def get_product_name(self, product_name):
        if product_name.startswith('.') or product_name.startswith(' ') or product_name[0].isdigit():
            product_name = product_name[1:]
            if product_name.startswith('.') or product_name.startswith(' ') or product_name[0].isdigit():
                return self.get_product_name(product_name)
            else:
                return product_name
        else:
            return product_name

    def sync_data_order(self, order_model, order, project, sale_orders_lines, lines, project_model, analytic_account,
                        project_tasks, i):
        # if order['state'] in ['draft', 'approval', 'approved']:
        #     order['state'] = 'draft'

        if 'user_id' in order and order['user_id']:
            # user = users.get(lead['user_id'][0], False)
            user = order_model.create_uid.search([('name', '=', order['user_id'][1])])
            if user:
                order['user_id'] = user.id
            else:
                order['user_id'] = 100

        else:
            order['user_id'] = 100

        if order['partner_id'] and len(order['partner_id']) > 0:
            partner_id = order_model.partner_id.search(
                [('name', '=', order['partner_id'][1].split('- ')[1].strip())],
                limit=1)
            if not partner_id:
                partner_id = order_model.partner_id.search(
                    [('name', 'like', order['partner_id'][1].split('- ')[1].strip())],
                    limit=1)
            if partner_id:
                order['partner_id'] = partner_id.id
            else:
                try:
                    if order['user_id'] != 100:
                        partner_id = user.partner_id.id
                        order['partner_id'] = partner_id.id
                    else:
                        usr = order_model.create_uid.search([('id', '=', 100)])
                        partner_id = usr.partner_id.id
                        order['partner_id'] = partner_id.id
                except Exception:
                    try:
                        order['partner_id'] = partner_id
                    except Exception:
                        pass
                if not partner_id:
                    try:
                        order['partner_id'] = user.id
                    except Exception:
                        pass

        if order['company_id'] and len(order['company_id']) > 0:
            del order['company_id']

        if order['team_id'] and len(order['team_id']) > 0:
            del order['team_id']

        del order['id']
        del order['sale_partner_id']
        del order['project_id']
        del order['project_project_id']

        if order['opportunity_id']:
            lead_id = self.env['crm.lead'].search([('id_lbs_connect', '=', order['opportunity_id'][0])], limit=1)
            if lead_id:
                order['opportunity_id'] = lead_id.id
            else:
                del order['opportunity_id']

        new_order = order_model.with_context(exchange=True).create(order)
        self.env.cr.execute("UPDATE sale_order SET create_date=%s WHERE id=%s", (order['create_date'], new_order.id))


        models_rpc, db, password, uid = connect()
        new_analityc_account = False
        if analytic_account:
            anac_partner = self.env['res.partner']
            if analytic_account[0]['partner_id']:
                anac_partner = order_model.partner_id.search(
                    [('name', 'like', analytic_account[0]['partner_id'][1].split('- ')[1].strip())], limit=1)

            new_analityc_account = new_order.analytic_account_id.create({
                'name': analytic_account[0]['name'],
                'partner_id': anac_partner.id,
                'active': True,
                'id_lbs_connect': analytic_account[0]['id']
            })
            new_analityc_account_moves = models_rpc.execute_kw(db, uid, password, 'account.analytic.line',
                                                               'search_read',
                                                               [[['account_id', '=',
                                                                  analytic_account[0]['id']]]])
            for move in new_analityc_account_moves:
                try:
                    move_user = order_model.user_id.search([('name', '=', move['user_id'][1])], limit=1)
                except Exception:
                    move_user = False
                move_partner = order_model.partner_id.search(
                    [('name', 'like', move['partner_id'][1].split('- ')[1].strip())], limit=1)
                try:
                    new_analityc_account.line_ids.create({
                        'name': move['name'],
                        'partner_id': move_partner.id,
                        'account_id': new_analityc_account.id,
                        'amount': move['amount'],
                        'unit_amount': move['unit_amount'],
                        'user_id': move_user.id if move_user.id else False,
                    })
                except Exception:
                    new_analityc_account.line_ids.create({
                        'name': move['name'],
                        'partner_id': move_partner.id,
                        'account_id': new_analityc_account.id,
                        'amount': move['amount'],
                        'unit_amount': move['unit_amount'],
                        'user_id': False,
                    })
            new_order.analytic_account_id = new_analityc_account

            if project:
                expenses = models_rpc.execute_kw(db, uid, password, 'account.move.line',
                                                 'search_read',
                                                 [[['analytic_account_id', '=', analytic_account[0]['id']]]])
                for expense in expenses:
                    if expense['debit']:
                        product=False
                        if expense['product_id']:
                            product = models_rpc.execute_kw(db, uid, password, 'product.product', 'search_read',
                                                            [[['id', '=', expense['product_id'][0]]]],
                                                            {'fields': fields_to_read_product,
                                                             'context': {'lang': 'uk_UA'}})
                        remove_digits = str.maketrans('', '', digits)

                        if product:
                            product_id = order_model.order_line.product_id.search(
                                [('name', '=', product[0]['name'])], limit=1)
                            product_name = product[0]['name']
                            if not product_id:
                                if product[0]['name'] == '1.1. Письмова консультація з правової ситуації':
                                    product_id = order_model.order_line.product_id.search(
                                        [('name', '=', 'Письмова консультація з правової ситуації')], limit=1)
                                else:
                                    # product_name = product_name.translate(remove_digits)
                                    product_name = self.get_product_name(product_name).strip()
                                    product_id = order_model.order_line.product_id.search(
                                        [('name', 'like', product_name)])
                                    if len(product_id) > 1:
                                        product_id = product_id.filtered(lambda l: l.default_code == '*arh')

                            if product[0]['name'] == 'Expenses':
                                product_id = order_model.order_line.product_id.search([('name', '=', 'Витрати')], limit=1)
                            if product_name == 'Оцінка податкового навантаження бізнесу з метою виявлення можливостей його оптимізації та розробка схем оптимізації':
                                product_id = order_model.order_line.product_id.search(
                                    [('name', 'like',
                                      'Оцінка податкового навантаження бізнесу та розробка схем оптимізації')])
                            if product_name == 'Попередня оплата':
                                product_id = order_model.order_line.product_id.search(
                                    [('name', 'like', 'Передоплата за послуги')])
                            if not product_id:
                                product_id = order_model.order_line.product_id.search([('name', '=', 'Витрати')], limit=1)
                        else:
                            product_id = order_model.order_line.product_id.search([('name', '=', 'Витрати')], limit=1)

                        if expense['partner_id']:
                            empl = self.env['hr.employee'].search(
                                [('name', 'like', expense['partner_id'][1].translate(
                                    remove_digits).replace('-', '').strip())]).id
                            if not empl:
                                empl = 143
                        else:
                            empl = 143
                        self.env['hr.expense'].create({
                            'name': expense['name'],
                            'product_id': product_id.id,
                            'analytic_account_id': new_analityc_account.id,
                            'unit_amount': expense['debit'],
                            'employee_id': empl,
                            'currency_id': 2,
                        })

        new_project = self.env['project.project']
        project_exist = False
        if project:
            project_user = self.env['res.users']
            if project[0]['user_id']:
                project_user = order_model.user_id.search([('name', '=', project[0]['user_id'][1])], limit=1)
            if project[0]['partner_id']:
                project_partner = order_model.partner_id.search(
                    [('name', 'like', project[0]['partner_id'][1].split('- ')[1].strip())], limit=1)
            else:
                project_partner = self.env['res.partner']
            project_exist = self.env['project.project'].search([('id_lbs_connect', '=', project[0]['id'])], limit=1)
            if project_exist:
                new_project = project_exist
            else:
                new_project = project_model.create({
                    'name': project[0]['name'],
                    'user_id': project_user.id,
                    'partner_id': project_partner.id,
                    'analytic_account_id': new_analityc_account.id if new_analityc_account else False,
                    'sale_order_id': new_order.id,
                    # 'state': project[0]['state']
                    'id_lbs_connect': project[0]['id']
                })
            new_order.project_id = new_project

        create_invoice = True
        try:
            if lines:
                for line in lines:
                    if not line['qty_invoiced']:
                        create_invoice = False
                    line['order_id'] = new_order.id
                    line['qty_delivered'] = line['qty_invoiced']
                new_order.order_line.create(lines)
        except Exception as e:
            _logger.error(line['product_id'])

        account = models_rpc.execute_kw(db, uid, password, 'account.invoice', 'search_read',
                                        [[['origin', '=', order['name']],['state','!=','cancel']]])

        if account and new_order.state == 'sale' and create_invoice:
            try:
                invoice_wizard = self.env['sale.advance.payment.inv'].with_context(active_ids=new_order.ids,
                                                                                   open_invoices=True).create({
                    'advance_payment_method': 'delivered'
                })
                res = invoice_wizard.create_invoices()
                new_account = self.env['account.move'].browse(res['res_id'])
                if new_account:
                    for account_line in new_account.invoice_line_ids:
                        if account_line.quantity != sum(account_line.sale_line_ids.mapped('qty_delivered')):
                            account_line.quantity = sum(account_line.sale_line_ids.mapped('qty_delivered'))
                            account_line._onchange_price_subtotal()
                    new_account._onchange_invoice_line_ids()
            except Exception as e:
                _logger.error(e)
            # for acc in account:
            #     if acc['amount_paid'] > 0:
            #         try:
            #             if acc['amount_paid'] == acc['amount_total']:
            #                 if new_account.state == 'draft':
            #                     new_account.action_post()
            #                 action_data = new_account.action_register_payment()
            #                 action_data['context']['default_amount'] = acc['amount_paid']
            #                 wizard = Form(self.env['account.payment.register'].with_context(action_data['context'])).save()
            #                 wizard.action_create_payments()
            #             else:
            #                 if acc['currency_id'][0] != 23:
            #                     if new_account.state == 'draft':
            #                         new_account.action_post()
            #                     action_data = new_account.action_register_payment()
            #                     action_data['context']['default_amount'] = acc['amount_paid']
            #                     wizard = Form(
            #                         self.env['account.payment.register'].with_context(action_data['context'])).save()
            #                     wizard.action_create_payments()
            #         except Exception as e:
            #             continue
            # account_lines = models_rpc.execute_kw(db, uid, password, 'account.invoice.line', 'search_read',
            #                                       [[[['invoice_id'][0], '=', acc['id']]]])
            #
            # account_partner = order_model.partner_id.search(
            #     [('name', 'like', acc['partner_id'][1].split('- ')[1].strip())], limit=1)
            # invoice_data = new_order.action_create_invoice()
            # invoice_data['context']['default_advanced_payment_method'] = 'delivered'

            # new_account = False
            # new_account = order_model.invoice_ids.create({
            #     'partner_id': account_partner.id,
            #     'move_type': acc['type'],
            #     'invoice_date': acc['date_invoice'],
            #     'invoice_user_id': new_order.user_id.id,
            #     'state': acc['state'] if acc['state'] != 'paid' else 'draft'
            # })
            # if account_lines and new_account:
            #     for acc_line in account_lines:
            #         product = models_rpc.execute_kw(db, uid, password, 'product.product', 'search_read',
            #                                         [[['id', '=', acc_line['product_id'][0]]]],
            #                                         {'fields': fields_to_read_product})
            #         remove_digits = str.maketrans('', '', digits)
            #         product_id = order_model.order_line.product_id.search(
            #             [('name', 'like', product[0]['name'])], limit=1)
            #         product_name = product[0]['name']
            #         product_name = product_name.translate(remove_digits)
            #         if not product_id:
            #             product_id = order_model.order_line.product_id.search(
            #                 [('name', 'like', product_name[3:].strip())])
            #         if product[0]['name'] == 'Expenses':
            #             product_id = order_model.order_line.product_id.search([('name', '=', 'Витрати')])
            #         if product[0]['name'] == '3.1. Представництво інтересів в органах':
            #             product_id = product_id[-1]
            #         if product_name == '..Супровід оформлення поділу/виділу об’єкта нерухомості ':
            #             product_id = order_model.order_line.product_id.search(
            #                 [('name', 'like',
            #                   'Супровід оформлення права на об’єкт нерухомості в результаті трансформації')])
            #         if product_name == '. Супровід створення господарських товариств/ кооперативу/ ФГ':
            #             product_id = order_model.order_line.product_id.search(
            #                 [('name', 'like', 'Супровід створення господарських товариств')])
            #         if product_name == '..Супровід врахування інтересів під час розроблення, погодження затвердження (внесення змін) до Зонінгу':
            #             product_id = order_model.order_line.product_id.search(
            #                 [(
            #                     'name', 'like',
            #                     'Супровід врахування інтересів Клієнта в містобудівній документації')])
            #         if product_name == '.. Письмова консультація з правової ситуації':
            #             product_id = product_id[0]
            #         if product_name == '. Оцінка податкового навантаження бізнесу з метою виявлення можливостей його оптимізації та розробка схем оптимізації':
            #             product_id = order_model.order_line.product_id.search(
            #                 [('name', 'like',
            #                   'Оцінка податкового навантаження бізнесу та розробка схем оптимізації')])
            #         if product_name == '..Супровід отримання лімітів на висотність об’єкту ':
            #             product_id = order_model.order_line.product_id.search(
            #                 [('name', 'like', 'Супровід отримання сертифіката про готовність')])
            #         if product_name == '.. Комплекс юридичних послуг щодо супроводу нового капітального будівництва об’єкта (реконструкції) з незначним класом наслідків (відповідальності) (СС)':
            #             product_id = order_model.order_line.product_id.search([('name', 'like',
            #                                                                     'Комплексний юридичний супровід нового капітального будівництва (реконструкції) об\'єкта (СС1)')])
            #         if product_name == '.. Комплекс юридичних послуг щодо супроводу нового капітального будівництва об’єкта (реконструкції) з середнім класом наслідків (відповідальності) (СС)':
            #             product_id = order_model.order_line.product_id.search([('name', 'like',
            #                                                                     'Комплексний юридичний супровід нового капітального будівництва (реконструкції) об\'єкта (СС2/СС3)')])
            #         if product_name == '.. Підготовка та супровід укладання договору оренди об’єкта нерухомості (складна конструкція)':
            #             product_id = order_model.order_line.product_id.search([('name', 'like',
            #                                                                     'Підготовка та супровід укладення договорів, пов’язаних із експлуатацією нерухомого майна')])
            #         if product_name == '..Письмова консультація з правової ситуації':
            #             product_id = product_id[1]
            #         if product_name == '..Супровід розроблення, погодження, затвердження (внесення змін) схеми планування території':
            #             product_id = order_model.order_line.product_id.search([('name', 'like',
            #                                                                     'Супровід розроблення, погодження')])
            #         if product_name == '. Супровід створення АТ, холдингових компаній':
            #             product_id = order_model.order_line.product_id.search([('name', 'like',
            #                                                                     'Супровід створення АТ')])
            #         if product_name == '..Супровід проведення технічної інвентаризації об’єкта нерухомості':
            #             product_id = order_model.order_line.product_id.search([('name', 'like',
            #                                                                     'Реєстрація права на об’єкт в Державному реєстрі речових прав на нерухоме майно з відкриттям розділу')])
            #         if product_name == '..Супровід отримання дозволу на зміну функціонального призначення  приміщення ':
            #             product_id = order_model.order_line.product_id.search([('name', 'like',
            #                                                                     'Супровід оформлення права на ТС')])
            #         if product_name == '..Супровід проведення громадських слухань':
            #             product_id = order_model.order_line.product_id.search([('name', 'like',
            #                                                                     'Супровід отримання контрольної картки')])
            #
            #         if product_name == '..Моделювання механізму фінансування будівельних проектів на базі інструменту – кооперативів':
            #             product_id = order_model.order_line.product_id.search([('name', 'like',
            #                                                                     'Представництво інтересів в органах влади')])
            #         if product_name == '..Підготовка та супровід укладання договору оренди об’єкта нерухомості (не складна конструкція)':
            #             product_id = order_model.order_line.product_id.search([('name', 'like',
            #                                                                     'Підготовка та супровід укладення договорів, пов’язаних із розпорядженням майном')])
            #         if product_name == 'Попередня оплата':
            #             product_id = order_model.order_line.product_id.search(
            #                 [('name', 'like', 'Передоплата за послуги')])
            #         if not product_id:
            #             prod_test = acc_line['name'].split(']')[1]
            #             prod_test = prod_test.translate(remove_digits)
            #             product_id = order_model.order_line.product_id.search(
            #                 [('name', 'like', prod_test[3:].strip())], limit=1)
            #             if not product_id:
            #                 pass
            #                 if prod_test == ' . Підготовка та супровід укладання договору щодо використання/відчуження майнових прав інтелектуальної власності на ТМ, КН, винахід, корисну модель, промисловий зразок, ГЗ, сорти рослин, породи тварин ':
            #                     product_id = order_model.order_line.product_id.search([('name', 'like',
            #                                                                             'Підготовка та супровід укладання договору щодо використання')],
            #                                                                           limit=1)
            #         # account_id = new_account.invoice_line_ids.account_id.search(
            #         #     [('code', '=', acc_line['account_id'][1].split()[0])])
            #         needed_order_line = new_order.order_line.filtered(
            #             lambda line: line.product_id.id == product_id.id)
            #         # if acc_line['discount_fixed'] != 0:
            #         #     acc_line['discount'] = round((((acc_line['discount_fixed'] * acc_line[
            #         #         'product_uom_qty']) / (acc_line['price_unit'] * acc_line[
            #         #         'product_uom_qty'])) * 100), 2)
            #         new_invoice_line = new_account.invoice_line_ids.create({
            #             'product_id': product_id.id,
            #             'move_id': new_account.id,
            #             'name': acc_line['name'],
            #             'price_unit': acc_line['price_unit'],
            #             'price_total': acc_line['price_total'],
            #             'price_subtotal': acc_line['price_subtotal'],
            #             'discount': acc_line['discount'],
            #             'quantity': acc_line['quantity'],
            #             'amount_currency': acc_line['price_total'],
            #             'balance': acc_line['price_total'],
            #             'account_id': 108,
            #             'discount_fixed': acc_line['discount_fixed'],
            #             'analytic_account_id': new_analityc_account.id,
            #         })
            #         needed_order_line.write({
            #             'invoice_lines': new_invoice_line.ids
            #         })

        if project_tasks and not project_exist:
            for task in project_tasks:
                try:
                    task_user = order_model.user_id.search([('name', '=', task['user_id'][1])], limit=1)
                except Exception:
                    task_user = False
                task_partner = self.env['res.partner']
                if task['partner_id']:
                    task_partner = order_model.partner_id.search(
                        [('name', 'like', task['partner_id'][1].split('- ')[1].strip())], limit=1)
                stage_id = False
                if task['stage_id']:
                    if task['stage_id'][0] == 24:
                        stage_id = 6
                try:
                    new_task = project_model.tasks.create({
                        'name': task['name'],
                        'project_id': new_project.id,
                        'partner_id': task_partner.id,
                        'user_id': task_user.id,
                        'planned_hours': task['planned_hours'],
                        'progress': task['progress'],
                        'sale_line_id': new_order.order_line[0].id if new_order.order_line else False,
                        'total_hours_spent': task['total_hours_spent'],
                        'analytic_account_id': new_analityc_account.id if new_analityc_account else False,
                        'sale_order_id': new_order.id,
                        'stage_id': stage_id if stage_id else 1
                    })
                except Exception:
                    new_task = project_model.tasks.create({
                        'name': task['name'],
                        'project_id': new_project.id,
                        'partner_id': task_partner.id,
                        'user_id': False,
                        'planned_hours': task['planned_hours'],
                        'progress': task['progress'],
                        'sale_line_id': new_order.order_line[0].id if new_order.order_line else False,
                        'total_hours_spent': task['total_hours_spent'],
                        'analytic_account_id': new_analityc_account.id if new_analityc_account else False,
                        'sale_order_id': new_order.id,
                        'stage_id': stage_id if stage_id else 1
                    })


                #
                #     new_timesheet = project_model.tasks.timesheet_ids.sudo().create({
                #     'name': timesheet['name'],
                #     'task_id': new_task.id,
                #     'project_id': new_project.id,
                #     # 'date': timesheet['date'],
                #     'employee_id': timesheet_user.employee_id.id,
                #     'unit_amount': 1,
                #     'timesheet_invoice_type': 'billable_fixed'
                # })

        if project and not project_exist:
            timesheetes = []
            timesheets = models_rpc.execute_kw(db, uid, password, 'account.analytic.line', 'search_read',
                                               [[['project_id', '=', project[0]['id']]]])
            for timesheet in timesheets:
                search_task = False
                if timesheet['task_id']:
                    search_task = new_project.task_ids.filtered(lambda l: l.id_lbs_connect == timesheet['task_id'][0])
                try:
                    timesheet_user = order_model.user_id.search([('name', '=', timesheet['user_id'][1])], limit=1)
                except Exception:
                    timesheet_user = False
                try:
                    timesheetes.append({
                        'name': timesheet['name'],
                        'task_id': search_task.id if search_task else False,
                        'project_id': new_project.id,
                        'date': timesheet['date'],
                        'employee_id': timesheet_user.employee_id.id if timesheet_user else new_project.user_id.employee_id.id,
                        'unit_amount': timesheet['unit_amount'],
                        'timesheet_invoice_type': 'billable_fixed'
                    })
                except Exception:
                    timesheetes.append({
                        'name': timesheet['name'],
                        'task_id': search_task.id if search_task else False,
                        'project_id': new_project.id,
                        'date': timesheet['date'],
                        'employee_id': timesheet_user.employee_id.id if timesheet_user else new_project.user_id.employee_id.id,
                        'unit_amount': timesheet['unit_amount'],
                        'timesheet_invoice_type': 'billable_fixed'
                    })
            new_order.timesheet_ids.sudo().create(timesheetes)



class Lead(models.Model):
    _inherit = "crm.lead"

    id_lbs_connect = fields.Integer(string='LBS connect ID')

    def get_product_name(self, product_name):
        if product_name.startswith('.') or product_name.startswith(' ') or product_name[0].isdigit():
            product_name = product_name[1:]
            if product_name.startswith('.') or product_name.startswith(' ') or product_name[0].isdigit():
                return self.get_product_name(product_name)
            else:
                return product_name
        else:
            return product_name

    def sync_leads(self, limit, offset):
        models_rpc, db, password, uid = connect()

        order_model = self.order_ids
        project_model = order_model.project_id
        crm_leads = models_rpc.execute_kw(db, uid, password, 'crm.lead', 'search_read',
                                          [[['stage_id', 'not in', [15, 16, 12]]]],
                                          {'fields': fields_to_read_crm, 'limit': limit, 'offset': offset, 'order': 'id'})

        if len(crm_leads) > 0:
            i = 1 + offset
            for lead in crm_leads:
                sync_data(self, lead)
                _logger.error('lead ' + str(i))
                i += 1

    def sync_orders(self, limit, offset, in_sale_status=False):
        models_rpc, db, password, uid = connect()

        order_model = self.order_ids
        project_model = order_model.project_id

        if not in_sale_status:
            sale_orders = models_rpc.execute_kw(db, uid, password, 'sale.order', 'search_read', [
                [['amount_total', '>', 1], ['state', 'in', ['draft', 'approval', 'approved', 'sent']]]],
                                                {'fields': fields_to_read_sale_order})
        else:
            sale_orders = models_rpc.execute_kw(db, uid, password, 'sale.order', 'search_read', [
                [['amount_total', '>', 1], ['state', '=', 'sale']]],
                                                 {'fields': fields_to_read_sale_order, 'limit': limit, 'offset': offset, 'order': 'id'})

        if len(sale_orders) > 0:
            i = 1 + offset
            for order in sale_orders:
                _logger.error('order ' + str(i))
                i += 1
                if order['state'] == 'sale':
                    if order['project_project_id']:
                        project = models_rpc.execute_kw(db, uid, password, 'project.project', 'search_read',
                                                        [[['state', 'not in', ['cancelled', 'done']],
                                                          ['id', '=', order['project_project_id'][0]]]])
                        if project:
                            pass
                        else:
                            continue
                    else:
                        if order['opportunity_id']:
                            opportunity_id = models_rpc.execute_kw(db, uid, password, 'crm.lead', 'search_read',
                                                            [[['id', '=', order['opportunity_id'][0]]]])
                            if opportunity_id:
                                if opportunity_id[0]['project_id']:
                                    order['project_project_id'] = opportunity_id[0]['project_id']
                                    project = models_rpc.execute_kw(db, uid, password, 'project.project', 'search_read',
                                                                    [[['id', '=', opportunity_id[0]['project_id'][0]]]])
                                    if not project:
                                        continue
                                    else:
                                        pass
                                else:
                                    continue
                            else:
                                continue
                        else:
                            continue
                if order['project_project_id'] != False:
                    project = models_rpc.execute_kw(db, uid, password, 'project.project', 'search_read',
                                                    [[['state', 'not in', ['cancelled', 'done']],
                                                      ['id', '=', order['project_project_id'][0]]]])
                    project_tasks = models_rpc.execute_kw(db, uid, password, 'project.task', 'search_read',
                                                          [[['project_id', '=', order['project_project_id'][0]]]])
                else:
                    project = False
                    project_tasks = False

                if order['project_id'] != False:
                    analytic_account = models_rpc.execute_kw(db, uid, password, 'account.analytic.account',
                                                             'search_read',
                                                             [[['id', '=', order['project_id'][0]]]])
                else:
                    analytic_account = False

                sale_orders_lines = models_rpc.execute_kw(db, uid, password, 'sale.order.line', 'search_read',
                                                          [[['order_id', '=', order['id']]]])
                lines = []
                if sale_orders_lines:
                    for line in sale_orders_lines:
                        product = models_rpc.execute_kw(db, uid, password, 'product.product', 'search_read',
                                                        [[['id', '=', line['product_id'][0]]]],
                                                        {'fields': fields_to_read_product,
                                                         'context': {'lang': 'uk_UA'}})
                        remove_digits = str.maketrans('', '', digits)

                        product_id = order_model.order_line.product_id.search(
                            [('name', '=', product[0]['name'])], limit=1)
                        product_name = product[0]['name']
                        if not product_id:
                            if product[0]['name'] == '1.1. Письмова консультація з правової ситуації':
                                product_id = order_model.order_line.product_id.search(
                                    [('name', '=', 'Письмова консультація з правової ситуації')], limit=1)
                            else:
                                # product_name = product_name.translate(remove_digits)
                                product_name = self.get_product_name(product_name).strip()
                                product_id = order_model.order_line.product_id.search(
                                    [('name', 'like', product_name)])
                                if len(product_id) > 1:
                                    product_id = product_id.filtered(lambda l: l.default_code == '*arh')

                        if product[0]['name'] == 'Expenses':
                            product_id = order_model.order_line.product_id.search([('name', '=', 'Витрати')])
                        if product_name == 'Оцінка податкового навантаження бізнесу з метою виявлення можливостей його оптимізації та розробка схем оптимізації':
                            product_id = order_model.order_line.product_id.search(
                                [('name', 'like',
                                  'Оцінка податкового навантаження бізнесу та розробка схем оптимізації')])
                        if product_name == 'Попередня оплата':
                            product_id = order_model.order_line.product_id.search(
                                [('name', 'like', 'Передоплата за послуги')])
                        if not product_id:
                            product_id = order_model.order_line.product_id.search([('name', '=', 'Витрати')])
                        # if line['discount_fixed'] != 0:
                        #     line['discount'] = round((((line['discount_fixed'] * line['product_uom_qty']) / (line['price_unit'] * line['product_uom_qty'])) * 100),2)
                        if product_id:
                            if product_id.product_tmpl_id.so_pdf_note != line['so_pdf_note']:
                                product_id.product_tmpl_id.so_pdf_note = line['so_pdf_note']
                            lines.append({
                                'product_id': product_id.id,
                                'product_uom_qty': line['product_uom_qty'],
                                # 'qty_delivered': line['qty_delivered'],
                                'qty_delivered': 0,
                                'qty_invoiced': line['qty_invoiced'],
                                'price_unit': line['price_unit'],
                                'discount': line['discount'],
                                'discount_fixed': line['discount_fixed'],
                                'name': line['name'],
                                'order_id': False,
                                'so_pdf_note': line['so_pdf_note']
                            })

                self.env['sale.order'].sync_data_order(order_model, order, project, sale_orders_lines, lines,
                                                       project_model,
                                                       analytic_account, project_tasks, i)


    def sync_projects(self, limit, offset):
        models_rpc, db, password, uid = connect()

        order_model = self.order_ids
        project_model = order_model.project_id

        project_ids = models_rpc.execute_kw(db, uid, password, 'project.project', 'search_read',
                                            [[['active', '=', True]]], {'limit': limit, 'offset': offset, 'order': 'id'})

        if len(project_ids) > 0:
            i = 1 + offset
            for project in project_ids:
                project_tasks = models_rpc.execute_kw(db, uid, password, 'project.task', 'search_read',
                                                      [[['project_id', '=', project['id']]]])
                self.env['project.project'].sync_data(project, project_tasks, order_model, project_model, i)
                _logger.error('project '+ str(i))
                i += 1

class Project(models.Model):
    _inherit = "project.project"

    id_lbs_connect = fields.Integer(string='LBS connect ID')

    def get_product_name(self, product_name):
        if product_name.startswith('.') or product_name.startswith(' ') or product_name[0].isdigit():
            product_name = product_name[1:]
            if product_name.startswith('.') or product_name.startswith(' ') or product_name[0].isdigit():
                return self.get_product_name(product_name)
            else:
                return product_name
        else:
            return product_name

    def sync_data(self, project, project_tasks, order_model, project_model, i):
        models_rpc, db, password, uid = connect()

        if self.search([('id_lbs_connect','=',project['id'])]):
            return

        try:
            project_user = self.env['res.users']
            if project['user_id']:
                project_user = order_model.user_id.search([('name', '=', project['user_id'][1])], limit=1)
            if project['partner_id']:
                project_partner = order_model.partner_id.search(
                    [('name', 'like', project['partner_id'][1].split('- ')[1].strip())], limit=1)
            else:
                project_partner = self.env['res.partner']

            new_analityc_account = self.env['account.analytic.account']
            if project['analytic_account_id']:
                analytic_acc_exist = self.env['account.analytic.account'].search(
                    [('id_lbs_connect', '=', project['analytic_account_id'][0])], limit=1)
                if analytic_acc_exist:
                    new_analityc_account = analytic_acc_exist
                else:
                    analytic_account = models_rpc.execute_kw(db, uid, password, 'account.analytic.account', 'search_read',
                                                             [[['id', '=', project['analytic_account_id'][0]]]])
                    anac_partner = self.env['res.partner']
                    if analytic_account[0]['partner_id']:
                        anac_partner = order_model.partner_id.search(
                            [('name', 'like', analytic_account[0]['partner_id'][1].split('- ')[1].strip())], limit=1)

                    new_analityc_account = self.env['account.analytic.account'].create({
                        'name': analytic_account[0]['name'],
                        'partner_id': anac_partner.id,
                        'active': True,
                        'id_lbs_connect': analytic_account[0]['id']
                    })
                    new_analityc_account_moves = models_rpc.execute_kw(db, uid, password, 'account.analytic.line',
                                                                       'search_read',
                                                                       [[['account_id', '=', analytic_account[0]['id']]]])
                    for move in new_analityc_account_moves:
                        try:
                            move_user = order_model.user_id.search([('name', '=', move['user_id'][1])], limit=1)
                        except Exception:
                            move_user = False
                        move_partner = self.env['res.partner']
                        if move['partner_id']:
                            move_partner = order_model.partner_id.search(
                                [('name', 'like', move['partner_id'][1].split('- ')[1].strip())], limit=1)
                        try:
                            new_analityc_account.line_ids.create({
                                'name': move['name'],
                                'partner_id': move_partner.id,
                                'account_id': new_analityc_account.id if new_analityc_account else False,
                                'amount': move['amount'],
                                'unit_amount': move['unit_amount'],
                                'user_id': move_user.id if move_user.id else False,
                            })
                        except Exception:
                            new_analityc_account.line_ids.create({
                                'name': move['name'],
                                'partner_id': move_partner.id,
                                'account_id': new_analityc_account.id if new_analityc_account else False,
                                'amount': move['amount'],
                                'unit_amount': move['unit_amount'],
                                'user_id': False,
                            })

                    expenses = models_rpc.execute_kw(db, uid, password, 'account.move.line',
                                                     'search_read',
                                                     [[['analytic_account_id', '=', analytic_account[0]['id']]]])
                    for expense in expenses:
                        if expense['debit']:
                            product = False
                            if expense['product_id']:
                                product = models_rpc.execute_kw(db, uid, password, 'product.product', 'search_read',
                                                                [[['id', '=', expense['product_id'][0]]]],
                                                                {'fields': fields_to_read_product, 'context': {'lang': 'uk_UA'}})
                            remove_digits = str.maketrans('', '', digits)

                            if product:
                                product_id = order_model.order_line.product_id.search(
                                    [('name', '=', product[0]['name'])], limit=1)
                                product_name = product[0]['name']
                                if not product_id:
                                    if product[0]['name'] == '1.1. Письмова консультація з правової ситуації':
                                        product_id = order_model.order_line.product_id.search(
                                            [('name', '=', 'Письмова консультація з правової ситуації')], limit=1)
                                    else:
                                        # product_name = product_name.translate(remove_digits)
                                        product_name = self.get_product_name(product_name).strip()
                                        product_id = order_model.order_line.product_id.search(
                                            [('name', 'like', product_name)])
                                        if len(product_id) > 1:
                                            product_id = product_id.filtered(lambda l: l.default_code == '*arh')

                                if product[0]['name'] == 'Expenses':
                                    product_id = order_model.order_line.product_id.search([('name', '=', 'Витрати')], limit=1)
                                if product_name == 'Оцінка податкового навантаження бізнесу з метою виявлення можливостей його оптимізації та розробка схем оптимізації':
                                    product_id = order_model.order_line.product_id.search(
                                        [('name', 'like',
                                          'Оцінка податкового навантаження бізнесу та розробка схем оптимізації')])
                                if product_name == 'Попередня оплата':
                                    product_id = order_model.order_line.product_id.search(
                                        [('name', 'like', 'Передоплата за послуги')])
                                if not product_id:
                                    product_id = order_model.order_line.product_id.search([('name', '=', 'Витрати')], limit=1)
                            else:
                                product_id = order_model.order_line.product_id.search([('name', '=', 'Витрати')], limit=1)
                            if expense['partner_id']:
                                empl = self.env['hr.employee'].search([('name', 'like', expense['partner_id'][1].translate(
                                    remove_digits).replace('-', '').strip())]).id
                                if not empl:
                                    empl = 143
                            else:
                                empl = 143
                            self.env['hr.expense'].create({
                                'name': expense['name'],
                                'product_id': product_id.id,
                                'analytic_account_id': new_analityc_account.id,
                                'unit_amount': expense['debit'],
                                'employee_id': empl,
                                'currency_id': 2,
                            })

            new_project = project_model.create({
                'name': project['name'],
                'user_id': project_user.id,
                'partner_id': project_partner.id,
                'analytic_account_id': new_analityc_account.id,
                # 'state': project['state']
                'id_lbs_connect': project['id']
            })

            for task in project_tasks:
                try:
                    task_user = order_model.user_id.search([('name', '=', task['user_id'][1])], limit=1)
                except Exception:
                    task_user = False
                task_partner = self.env['res.partner']
                if task['partner_id']:
                    task_partner = order_model.partner_id.search(
                        [('name', 'like', task['partner_id'][1].split('- ')[1].strip())], limit=1)
                stage_id = False
                if task['stage_id']:
                    if task['stage_id'][0] == 24:
                        stage_id = 6
                try:
                    new_task = project_model.tasks.create({
                        'name': task['name'],
                        'project_id': new_project.id,
                        'partner_id': task_partner.id,
                        'user_id': task_user.id,
                        'planned_hours': task['planned_hours'],
                        'progress': task['progress'],
                        'total_hours_spent': task['total_hours_spent'],
                        'analytic_account_id': new_analityc_account.id if new_analityc_account else False,
                        'stage_id': stage_id if stage_id else 1,
                        'id_lbs_connect': task['id']
                    })
                except Exception:
                    new_task = project_model.tasks.create({
                        'name': task['name'],
                        'project_id': new_project.id,
                        'partner_id': task_partner.id,
                        'user_id': False,
                        'planned_hours': task['planned_hours'],
                        'progress': task['progress'],
                        'total_hours_spent': task['total_hours_spent'],
                        'analytic_account_id': new_analityc_account.id if new_analityc_account else False,
                        'stage_id': stage_id if stage_id else 1,
                        'id_lbs_connect': task['id']
                    })

            timesheetes = []
            timesheets = models_rpc.execute_kw(db, uid, password, 'account.analytic.line', 'search_read',
                                               [[['project_id', '=', project['id']]]])
            for timesheet in timesheets:
                search_task = False
                if timesheet['task_id']:
                    search_task = new_project.task_ids.filtered(lambda l: l.id_lbs_connect == timesheet['task_id'][0])
                try:
                    timesheet_user = order_model.user_id.search([('name', '=', timesheet['user_id'][1])], limit=1)
                except Exception:
                    timesheet_user = False
                try:
                    timesheetes.append({
                        'name': timesheet['name'],
                        'task_id': search_task.id if search_task else False,
                        'project_id': new_project.id,
                        'date': timesheet['date'],
                        'employee_id': timesheet_user.employee_id.id if timesheet_user else new_project.user_id.employee_id.id,
                        'unit_amount': timesheet['unit_amount'],
                        'timesheet_invoice_type': 'billable_fixed'
                    })
                except Exception:
                    timesheetes.append({
                        'name': timesheet['name'],
                        'task_id': search_task.id if search_task else False,
                        'project_id': new_project.id,
                        'date': timesheet['date'],
                        'employee_id': timesheet_user.employee_id.id if timesheet_user else new_project.user_id.employee_id.id,
                        'unit_amount': timesheet['unit_amount'],
                        'timesheet_invoice_type': 'billable_fixed'
                    })
            self.env['account.analytic.line'].sudo().create(timesheetes)

        except Exception as e:
            _logger.error('error error error error error error error error error error error error error error error error error error error error error error error error error error error error error error error error error error error ' + str(project['id']))


class ProjectTaskInherit(models.Model):
    _inherit = 'project.task'

    id_lbs_connect = fields.Integer()


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    id_lbs_connect = fields.Integer(string='LBS connect ID')
