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

class ProjectTask(models.Model):
    _inherit = "project.task"
    ticket_no = fields.Char(string="No. Ticket", related="helpdesk_ticket_id.ticket_ref")
    date_ahora = fields.Datetime()
    user_id = fields.Many2one('res.users')
    nombre_del_solicitante = fields.Char(string="Nombre del solicitante", related="helpdesk_ticket_id.x_studio_nombre_del_solicitante")
    clinica_solicitante = fields.Selection("Clinica solicitante", related="helpdesk_ticket_id.x_studio_clinica_solicitante")
    timeline_ids = fields.One2many('project.timeline.mod','timeline_project_id')
    def write(self, vals):
        teams = super(ProjectTask, self).write(vals)
        if not self.timeline_ids:
            self._create_projecttime()
        return teams

    @api.onchange('stage_id')
    def test_mod_help(self):
        self._create_projecttime()
    
    def _create_projecttime(self):
        vals_list = {}
        for a in self:
            vals_list = {
                'timeline_project_id': self._origin.id,
                'ticket_id': a.helpdesk_ticket_id.id,
                'ticket_name': a.helpdesk_ticket_id.name,
                'ticket_no': a.helpdesk_ticket_id.ticket_ref,
                'ticket_asignado': a.helpdesk_ticket_id.user_id.id,
                'piloto':a.x_studio_nombre_del_piloto,
                'circuito': a.x_studio_circuito,
                'partner_id': a.partner_id.id,
                'stage_id': a.stage_id.id,
                'template_work_id': a.worksheet_template_id.id,
                'dpi': a.x_studio_dpi,
                'tel': a.partner_phone,
                'tel_2': a.x_studio_telefono_2,
                'forma_pago': a.x_studio_forma_de_pago,
                'monto': a.x_studio_monto,
                'direccion_d': a.x_studio_direccin_de_despacho,
                'observacion': a.x_studio_observaciones_generales_para_entrega,
                'articulo_venta': a.sale_line_id.id,
                'ticket_servicio': a.x_studio_many2one_field_HP9MJ.id,
            }
        self.timeline_ids.create(vals_list)


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
                'dpi': self.x_studio_dpi,
                'telefono': self.x_studio_telfono,
                'telefono2': self.x_studio_tel_2,
                'monto': self.x_studio_monto,
                'dir_despacho': self.x_studio_direccin_de_despacho,
                'quien_recibe': self.x_studio_nombre_de_quien_recibe,
                'observaciones': self.x_studio_observaciones_generales_para_entrega,
                'fecha_entrega': self.x_studio_fecha_solicitada_de_entrega,
                #'forma_pago':self.x_studio_forma_de_pago_1,
                'asignado':self.x_studio_asignado_para_hoy
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
                'default_dpi': self.x_studio_dpi,
                'default_telefono': self.x_studio_telfono,
                'default_telefono2': self.x_studio_tel_2,
                'default_monto': self.x_studio_monto,
                'default_dir_despacho': self.x_studio_direccin_de_despacho,
                'default_quien_recibe': self.x_studio_nombre_de_quien_recibe,
                'default_observaciones': self.x_studio_observaciones_generales_para_entrega,
                'default_fecha_entrega': self.x_studio_fecha_solicitada_de_entrega,
                'default_forma_pago':self.x_studio_forma_de_pago,
                'default_asignado':self.x_studio_asignado_para_hoy,

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
            'x_studio_dpi': self.dpi,
            'partner_phone': self.telefono,
            'x_studio_telefono_2': self.telefono2,
            'x_studio_monto': self.monto,
            'x_studio_direccin_de_despacho': self.dir_despacho,
            'x_studio_nombre_de_quien_recibe': self.quien_recibe,
            'x_studio_observaciones_generales_para_entrega': self.observaciones,
            'x_studio_fecha_solicitada_de_entrega': self.fecha_entrega,
            'x_studio_forma_de_pago': self.forma_pago,
            'x_studio_asignado_para_hoy_1': self.asignado,
        }
        
    
class helpdeskTimeline(models.Model):
    _name = "helpdesk.timeline.mod"
    
    timeline_help_id = fields.Many2one('helpdesk.ticket')
    department_id = fields.Many2one('res.country.state', related='timeline_help_id.x_studio_many2one_field_jBSNT', string="Departamento")
    municipality_id = fields.Many2one('x_res_municipality', related='timeline_help_id.x_studio_municipio', string="Municipio")
    zone_id = fields.Many2one('x_res_zone', related='timeline_help_id.x_studio_zona_2', string="Zona")
    area_solicitant = fields.Selection(string='Area solicitante', related='timeline_help_id.x_studio_clinica_solicitante')
    name_solicitant = fields.Char(string='Nombre solicitante', related='timeline_help_id.x_studio_nombre_del_solicitante')
    partner_id = fields.Many2one("res.partner", string="Cliente", related='timeline_help_id.partner_id')
    request_delivery_date = fields.Date(string='Fecha solicitada de entrega', related='timeline_help_id.x_studio_fecha_solicitada_de_entrega')
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


class projectTimeline(models.Model):
    _name = "project.timeline.mod"

    timeline_project_id = fields.Many2one('project.task')
    users_id = fields.Many2one('res.users')
    ticket_name = fields.Char(string='Nombre de ticket')
    ticket_id = fields.Integer(string='Id de ticket', default=0)
    ticket_no = fields.Char(string='No. ticket')
    ticket_asignado = fields.Many2one('res.users', string='Asignado')
    piloto = fields.Char(string='Piloto')
    circuito = fields.Char(string='Circuito')
    partner_id = fields.Many2one('res.partner', string="Cliente")
    stage_id = fields.Many2one('project.task.type')
    project_id = fields.Many2one('project.project', related='timeline_project_id.project_id', string="Proyecto")
    template_work_id = fields.Many2one('worksheet.template')
    dpi = fields.Char(string='DPI')
    tel = fields.Char(string='Teléfono')
    tel_2 = fields.Char(string='Teléfono 2')
    forma_pago = fields.Char(string='Forma de pago')
    monto = fields.Char(string='Monto')
    direccion_d = fields.Char(string='Dirección de despacho')
    observacion = fields.Char(string='Observaciones generales para entrega')
    asignado_hoy = fields.Selection(string='Asignado para hoy', related='timeline_project_id.x_studio_asignado_para_hoy_1')
    fecha_entrega = fields.Date(string='Fecha solicitada de entrega', related='timeline_project_id.x_studio_fecha_solicitada_de_entrega')
    articulo_venta = fields.Many2one('sale.order.line', string='Articulo en la orden de venta')
    etiqueta = fields.Many2many('project.tags',related='timeline_project_id.tag_ids',string='Etiquetas')
    ticket_servicio = fields.Many2one('helpdesk.ticket', related='timeline_project_id.x_studio_many2one_field_HP9MJ',string='Ticket se servicio de asistencia')