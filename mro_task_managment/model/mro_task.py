# -*- coding: utf-8 -*-
#################################################################################
#
# Copyright (c) 2015-Present TidyWay Software Solution. (<https://tidyway.in/>)
#
#################################################################################
import time
from datetime import datetime

from odoo import fields, models, api, _ 
from odoo import tools
from odoo.exceptions import Warning

class mro_work(models.Model):
    _name = "mro.task.work"
    _description = "MRO Task Work"

#     @api.model
#     def get_user_related_details(self):
#         res = {}
#         emp_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)])
#         if not emp_id:
#             raise Warning(_('Please define employee for user "%s". You must create one.') % (self.env.user.name,))
#         if not emp_id.product_id:
#             raise Warning(_('Please define product and product category property account on the related employee.\nFill in the HR Settings tab of the employee form.'))
# 
#         if not emp_id.journal_id:
#             raise Warning(_('Please define journal on the related employee.\nFill in the timesheet tab of the employee form.'))
# 
#         acc_id = emp_id.product_id.property_account_expense.id
#         if not acc_id:
#             acc_id = emp_id.product_id.categ_id.property_account_expense_categ.id
#             if not acc_id:
#                 raise Warning(_('Please define product and product category property account on the related employee.\nFill in the timesheet tab of the employee form.'))
# 
#         res['product_id'] = emp_id.product_id.id
#         res['journal_id'] = emp_id.journal_id.id
#         res['general_account_id'] = acc_id
#         res['product_uom_id'] = emp_id.product_id.uom_id.id
#         return res

    @api.one
    @api.depends('initial_time', 'end_time')
    def _total_duration(self):
        for history in self:
            if not history.initial_time:
                raise Warning(_('Initial Time Format Incorrect!\nFormat must be HH:MM:SS'))
            if not history.end_time:
                raise Warning(_('End Time Format Incorrect!\nFormat must be HH:MM:SS'))
            start = datetime.strptime(history.date + ' ' + history.initial_time, '%Y-%m-%d %H:%M:%S')
            ends = datetime.strptime(history.date + ' ' + history.end_time, '%Y-%m-%d %H:%M:%S')
            history.duration = str(ends - start)

    @api.onchange('initial_time')
    def initialtime_onchange(self):
        if not self.initial_time:
            raise Warning(_('Initial Time Format Incorrect!\nFormat must be HH:MM:SS'))
        initial_time = self.initial_time.split(':')
        if len(initial_time) <> 3:
            raise Warning(_('Initial Time Format Incorrect!\nFormat must be HH:MM:SS'))
        if len(initial_time[0]) <> 2 or len(initial_time[1]) <> 2 or len(initial_time[2]) <> 2:
            raise Warning(_('Initial Time Format Incorrect!\nFormat must be HH:MM:SS'))
        if (not initial_time[0].isdigit()) or (not initial_time[1].isdigit()) or (not initial_time[2].isdigit()):
            raise Warning(_('Initial Time Format Incorrect!\nFormat must be HH:MM:SS in digit(numeric) format.'))
        if not (0 <= int(initial_time[0]) <= 23):
            raise Warning(_('Initial Time Format Incorrect!\nHH in between 0 to 23.'))
        if not (0 <= int(initial_time[1]) <= 59):
            raise Warning(_('Initial Time Format Incorrect!\nMM in between 0 to 59.'))
        if not (0 <= int(initial_time[2]) <= 59):
            raise Warning(_('Initial Time Format Incorrect!\nSS in between 0 to 59.'))

    @api.onchange('end_time')
    def endtime_onchange(self):
        if not self.end_time:
            raise Warning(_('End Time Format Incorrect!\nFormat must be HH:MM:SS'))
        end_time = self.end_time.split(':')
        if len(end_time) <> 3:
            raise Warning(_('End Time Format Incorrect!\nFormat must be HH:MM:SS'))
        if len(end_time[0]) <> 2 or len(end_time[1]) <> 2 or len(end_time[2]) <> 2:
            raise Warning(_('End Time Format Incorrect!\nFormat must be HH:MM:SS'))
        if (not end_time[0].isdigit()) or (not end_time[1].isdigit()) or (not end_time[2].isdigit()):
            raise Warning(_('End Time Format Incorrect!\nFormat must be HH:MM:SS in digit(numeric) format.'))
        if not (0 <= int(end_time[0]) <= 23):
            raise Warning(_('End Time Format Incorrect!\nHH in between 0 to 23.'))
        if not (0 <= int(end_time[1]) <= 59):
            raise Warning(_('End Time Format Incorrect!\nMM in between 0 to 59.'))
        if not (0 <= int(end_time[2]) <= 59):
            raise Warning(_('End Time Format Incorrect!\nSS in between 0 to 59.'))

    @api.one
    @api.depends('initial_time', 'end_time')
    def _total_duration_seconds(self):
        for history in self:
            if not history.initial_time:
                raise Warning(_('Initial Time Format Incorrect!\nFormat must be HH:MM:SS'))
            if not history.end_time:
                raise Warning(_('End Time Format Incorrect!\nFormat must be HH:MM:SS'))
            start = datetime.strptime(history.date + ' ' + history.initial_time, '%Y-%m-%d %H:%M:%S')
            ends = datetime.strptime(history.date + ' ' + history.end_time, '%Y-%m-%d %H:%M:%S')
            history.duration_seconds = str((ends - start).seconds)

    user_id = fields.Many2one('res.users', 'Done by', required=True, default=lambda self: self.env.user)
    name = fields.Char('Work summary')
    date = fields.Date('Date', default=lambda *a: time.strftime('%Y-%m-%d'))
    initial_time = fields.Char('Initial Time', default='00:00:00')
    end_time = fields.Char('End Time', default='00:00:00')
    duration = fields.Char(compute='_total_duration', string='Duration', store=True)
    duration_seconds = fields.Char(compute='_total_duration_seconds', string='Duration(Seconds)', store=True)
    company_id = fields.Many2one(related='task_id.company_id', string='Company', store=True, readonly=True)
    task_id = fields.Many2one('mro.order', 'Labor Task', ondelete='cascade')

    _order = "create_date desc"

    @api.model
    def _get_total_duration(self, task_id):
        task_obj = self.env['mro.task.work']
        task_record = task_obj.browse(task_id)
        start = datetime.strptime(task_record.date + ' ' + task_record.initial_time, '%Y-%m-%d %H:%M:%S')
        ends = datetime.strptime(task_record.date + ' ' + task_record.end_time, '%Y-%m-%d %H:%M:%S')
        values_to_replace = (ends - start).seconds
        return values_to_replace / 3600.0

    @api.model
    def _create_timesheet(self, work_line):
        analytic_line_obj = self.env['account.analytic.line']
        product_obj = self.env['product.product']
        #result = self.get_user_related_details()
        maintanance_order = work_line.task_id
        total_duration = self._get_total_duration(work_line.id)
        #prod = product_obj.browse(result['product_id'])
        analytic_line_obj.create({
            'name': tools.ustr(work_line.name),
            'user_id': work_line.user_id.id,
            'date' : work_line.date,
            'mro_id': maintanance_order.id,
            #'journal_id': result['journal_id'],
            #'amount': prod.standard_price * total_duration,  # (current_rec.duration) * (maintanance_order.costing_product_id.standard_price or 0.0),
            'account_id': maintanance_order.analytic_account_id and maintanance_order.analytic_account_id.id or False,
            #'general_account_id': result['general_account_id'],
            'ref': work_line.user_id.name,
            #'product_id': result['product_id'],
            'unit_amount': total_duration,
            #'product_uom_id': result['product_uom_id'],
            'mro_task_id': work_line.id
        })
        return True

    @api.model
    def _check_format(self, vals):
        if vals.get('initial_time'):
            initial_time = vals['initial_time'].split(':')
            if not initial_time:
                raise Warning(_('Initial Time Format Incorrect!\nFormat must be HH:MM:SS'))
            if len(initial_time) <> 3:
                raise Warning(_('Initial Time Format Incorrect!\nFormat must be HH:MM:SS'))
            if len(initial_time[0]) <> 2 or len(initial_time[1]) <> 2 or len(initial_time[2]) <> 2:
                raise Warning(_('Initial Time Format Incorrect!\nFormat must be HH:MM:SS'))
            if (not initial_time[0].isdigit()) or (not initial_time[1].isdigit()) or (not initial_time[2].isdigit()):
                raise Warning(_('Initial Time Format Incorrect!\nFormat must be HH:MM:SS in digit(numeric) format.'))
            if not (0 <= int(initial_time[0]) <= 23):
                raise Warning(_('Initial Time Format Incorrect!\nHH in between 0 to 23.'))
            if not (0 <= int(initial_time[1]) <= 59):
                raise Warning(_('Initial Time Format Incorrect!\nMM in between 0 to 59.'))
            if not (0 <= int(initial_time[2]) <= 59):
                raise Warning(_('Initial Time Format Incorrect!\nSS in between 0 to 59.'))
        if vals.get('end_time'):
            end_time = vals['end_time'].split(':')
            if not end_time:
                raise Warning(_('End Time Format Incorrect!\nFormat must be HH:MM:SS'))
            if len(end_time) <> 3:
                raise Warning(_('End Time Format Incorrect!\nFormat must be HH:MM:SS'))
            if len(end_time[0]) <> 2 or len(end_time[1]) <> 2 or len(end_time[2]) <> 2:
                raise Warning(_('End Time Format Incorrect!\nFormat must be HH:MM:SS'))
            if (not end_time[0].isdigit()) or (not end_time[1].isdigit()) or (not end_time[2].isdigit()):
                raise Warning(_('End Time Format Incorrect!\nFormat must be HH:MM:SS in digit(numeric) format.'))
            if not (0 <= int(end_time[0]) <= 23):
                raise Warning(_('End Time Format Incorrect!\nHH in between 0 to 23.'))
            if not (0 <= int(end_time[1]) <= 59):
                raise Warning(_('End Time Format Incorrect!\nMM in between 0 to 59.'))
            if not (0 <= int(end_time[2]) <= 59):
                raise Warning(_('End Time Format Incorrect!\nSS in between 0 to 59.'))
        if vals.get('initial_time') and vals.get('end_time'):
            timestart = datetime.strptime(vals['initial_time'], '%H:%M:%S')
            timeend = datetime.strptime(vals['end_time'], '%H:%M:%S')
            if timestart > timeend:
                raise Warning(_('Validation Error!\nEnd Time must be bigger Then Initial Time'))
        return True

    @api.model
    def create(self, vals):
        if not vals.get('initial_time'):
            raise Warning(_('Initial Time Format Incorrect!\nFormat must be HH:MM:SS'))
        if not vals.get('end_time'):
            raise Warning(_('End Time Format Incorrect!\nFormat must be HH:MM:SS'))
        self._check_format(vals)
        res_id = super(mro_work, self).create(vals)
        self._create_timesheet(res_id)
        return res_id

    @api.model
    def _check_start_end_time(self, vals):
        if vals.get('initial_time') and vals.get('end_time'):
            timestart = datetime.strptime(vals['initial_time'], '%H:%M:%S')
            timeend = datetime.strptime(vals['end_time'], '%H:%M:%S')
            if timestart > timeend:
                raise Warning(_('Validation Error!\nEnd Time must be bigger Then Initial Time'))
        elif vals.get('initial_time'):
            timestart = datetime.strptime(vals['initial_time'], '%H:%M:%S')
            timeend = datetime.strptime(self.end_time, '%H:%M:%S')
            if timestart > timeend:
                raise Warning(_('Validation Error!\nEnd Time must be bigger Then Initial Time'))
        elif vals.get('end_time'):
            timestart = datetime.strptime(self.initial_time, '%H:%M:%S')
            timeend = datetime.strptime(vals['end_time'], '%H:%M:%S')
            if timestart > timeend:
                raise Warning(_('Validation Error!\nEnd Time must be bigger Then Initial Time'))
        return True

    @api.one
    def _update_old_timesheet(self):
        analytic_line_obj = self.env['account.analytic.line']
        old_task = analytic_line_obj.search([('mro_task_id', '=', self.id)])
        if old_task:
            #product_obj = self.pool['product.product']
            #result = self.get_user_related_details()
            total_duration = self._get_total_duration(self.id)
            #prod = product_obj.browse(result['product_id'])
            old_task.write({
                                'name': tools.ustr(self.name),
                                'date' : self.date,
                                'ref': self.user_id.name,
                                'user_id': self.user_id.id,
                                'unit_amount': total_duration,
                            })
        return True

    @api.multi
    def write(self, vals):
        if vals.get('initial_time') or vals.get('end_time'):
            self._check_format(vals)
        self._check_start_end_time(vals)
        res = super(mro_work, self).write(vals)
        #if vals.get('initial_time') or vals.get('end_time'):
        self._update_old_timesheet()
        return res

class mro_order(models.Model):
    _inherit = 'mro.order'

    @api.model
    def getParentAnalyticMaintanance(self):
        md = self.env['ir.model.data']
        try:
            dummy, res_id = md.get_object_reference('mro_task_managment', 'maintanance_order_analytic')
            # search on id found in result to check if current user has read access right
            check_right = self.env['account.analytic.account'].search([('id', '=', res_id)])
            if check_right:
                return res_id
        except ValueError:
            pass
        return False

    @api.model
    def generate_analytic_account(self):
        all_mro_orders = self.sudo().search([])
        analytic_obj = self.env['account.analytic.account']
        for order in all_mro_orders:
            if not order.analytic_account_id:
                analytic_id = analytic_obj.create({
                                                  'name': order.name,
                                                  'mro_id': order.id,
                                                  'parent_id': self.getParentAnalyticMaintanance()
                                                  })
                order.write({
                             'analytic_account_id': analytic_id.id
                             })
        return True

    @api.model
    def format_seconds_to_hhmmss(self, seconds):
        hours = seconds // (60 * 60)
        seconds %= (60 * 60)
        minutes = seconds // 60
        seconds %= 60
        return "%02i:%02i:%02i" % (hours, minutes, seconds)

    @api.one
    def _total_hours_spent(self):
        for mro in self:
            total_duration = 0
            for line in mro.work_ids:
                total_duration += int(line.duration_seconds)
            mro.total_hours_spent = self.format_seconds_to_hhmmss(total_duration)

    work_ids = fields.One2many('mro.task.work', 'task_id', 'Work done')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    total_hours_spent = fields.Char(compute='_total_hours_spent', string='Total Hour(s) Spent', help="Total Time Spent")

    @api.model
    def _create_analytic_account(self, account_name):
        account_id = self.env['account.analytic.account'].create({
                                                                      'name': "/",
                                                                  })
        return account_id.id

    @api.model
    def create(self, vals):
        vals['analytic_account_id'] = self._create_analytic_account(vals.get('name'))
        res_id = super(mro_order, self).create(vals)
        res_id.analytic_account_id.write({
                                          'name': res_id.name,
                                          'mro_id': res_id.id,
                                          })
        return res_id

class account_analytic_account(models.Model):
    _inherit = 'account.analytic.account'
    mro_id = fields.Many2one('mro.order', 'Maintenance Orders')

class account_analytic_line(models.Model):
    _inherit = 'account.analytic.line'
    mro_id = fields.Many2one('mro.order', 'Maintenance Orders')
    mro_task_id = fields.Many2one('mro.task.work', 'MRO Task')

# class hr_analytic_timesheet(models.Model):
#     _inherit = 'hr.analytic.timesheet'
#     mro_task_id = fields.Many2one('mro.task.work', 'MRO Task'),
