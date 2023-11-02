# -*- coding: utf-8 -*-
from datetime import timedelta
from itertools import groupby
from markupsafe import Markup

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command
from odoo.osv import expression
from odoo.tools import float_is_zero, format_amount, format_date, html_keep_url, is_html_empty
from odoo.tools.sql import create_index
import logging
from odoo.addons.payment import utils as payment_utils

from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

class helpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"
    
    timeline_help_ids = fields.One2many('helpdesk.timeline.mod','timeline_help_id')
    team_new = fields.Char()
    team_old = fields.Char()

    def write(self, vals):
        teams = super(helpdeskTicket, self).write(vals)
        if not self.timeline_help_ids:
            self._create_helptime()
        return teams
    
    @api.onchange('team_id')
    def team_mod_help(self):
        for record in self:
            if not record.team_new:
                record.team_old = record.team_id.name
            else:
                record.team_old = record.team_new
            record.team_new = record.team_id.name
            if record.team_old != record.team_new:
                record._create_helptime()

    @api.onchange('stage_id')
    def test_mod_help(self):
        self._create_helptime()
    
    def _create_helptime(self):
        vals_list = {}
        for a in self:
            id_self = a.id
            _logger.info('//////////////////////////////////Create %s', self._origin.id)
            active_id =  self.env.context.get('active_id')
            vals_list = {
                'timeline_help_id': self._origin.id,
                'stage_id': a.stage_id.id,
                'create_uid': a.create_uid.id,
                'users_id': a.user_id.id,
                'team_id':a.team_id.id,
                'dpi': self.dpi_number,
                'telefono': self.phone,
                'telefono2': self.phone2,
                'monto': self.amount,
                'dir_despacho': self.street_dispach,
                'quien_recibe': self.who_receives,
                'observaciones': self.general_delivery_remarks,
                'fecha_entrega': self.date_delivery,
                #'forma_pago':self.payment_way_1,
                'asignado':self.assigned_today
            }
        self.timeline_help_ids.create(vals_list)
    
    def open_view_detail_helptime(self):
        return {
            'name': f"""Detalles""",
            'res_model': 'helpdesk.timeline.mod',
            'view_mode': 'tree,form',
            'target': 'current',
            # 'view_id': False,
            'view_id': self.env.ref('l10n_xma_mod_field_service.helpdesk_timeline_mod_tree').id,
            'views': [
                (self.env.ref('l10n_xma_mod_field_service.helpdesk_timeline_mod_tree').id, 'tree'),
               # (self.env.ref('treasury.treasury_lines_form').id, 'form'),
            ],
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', [lines.id for lines in self.timeline_help_ids])],
            'context': {
                'group_by': ['stage_id']
            }
        }
    
    def action_generate_fsm_task(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create a Field Service task'),
            'res_model': 'helpdesk.create.fsm.task',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'use_fsm': True,
                'default_helpdesk_ticket_id': self.id,
                'default_user_id': False,
                'default_partner_id': self.partner_id.id if self.partner_id else False,
                'default_name': self.name,
                'default_project_id': self.team_id.fsm_project_id.id,
                'default_dpi': self.dpi_number,
                'default_telefono': self.phone,
                'default_telefono2': self.phone2,
                'default_monto': self.amount,
                'default_dir_despacho': self.street_dispach,
                'default_quien_recibe': self.who_receives,
                'default_observaciones': self.general_delivery_remarks,
                'default_fecha_entrega': self.date_delivery,
                'default_forma_pago':self.payment_way,
                'default_asignado':self.assigned_today,

            }
        }
        
class CreateTask(models.TransientModel):
    _inherit = "helpdesk.create.fsm.task"   
    
    dpi = fields.Char()
    telefono = fields.Char()
    telefono2 = fields.Char()
    forma_pago = fields.Char()
    monto = fields.Float()
    dir_despacho = fields.Char()
    quien_recibe = fields.Char()
    observaciones = fields.Char()
    asignado = fields.Selection([
                                ('Si', 'Si'),
                                ('No', 'No'),
                                ])
    fecha_entrega= fields.Date()
    
    
    def _generate_task_values(self):
        self.ensure_one()
        return {
            'name': self.name,
            'helpdesk_ticket_id': self.helpdesk_ticket_id.id,
            'project_id': self.project_id.id,
            'partner_id': self.partner_id.id,
            'description': self.helpdesk_ticket_id.description,
            'dpi_number': self.dpi,
            'partner_phone': self.telefono,
            'partner_phone2': self.telefono2,
            'amount': self.monto,
            'street_dispach': self.dir_despacho,
            'who_receives': self.quien_recibe,
            'general_delivery_remarks': self.observaciones,
            'date_delivery': self.fecha_entrega,
            'payment_way': self.forma_pago,
            'assigned_today_1': self.asignado,
        }
        
    
class helpdeskTimeline(models.Model):
    _name = "helpdesk.timeline.mod"
    
    timeline_help_id = fields.Many2one('helpdesk.ticket')
    name_help_id = fields.Char(related='timeline_help_id.name', string="Nombre de Ticket")
    reference_help_id = fields.Char(related='timeline_help_id.ticket_ref', string="Número de Ticket")
    timeline_id_b = fields.Many2one('helpdesk.ticket')
    name=fields.Char()
    stage_id = fields.Many2one('helpdesk.stage')
    Datetime = fields.Datetime()
    users_id = fields.Many2one('res.users')
    create_uid = fields.Many2one('res.users')
    team_id = fields.Many2one('helpdesk.team')
    dpi = fields.Char()
    telefono = fields.Char()
    telefono2 = fields.Char()
    forma_pago = fields.Char()
    monto = fields.Float()
    dir_despacho = fields.Char()
    quien_recibe = fields.Char()
    observaciones = fields.Char()
    asignado = fields.Selection([
                                ('Si', 'Si'),
                                ('No', 'No'),
                                ])
    fecha_entrega= fields.Date()
    
    