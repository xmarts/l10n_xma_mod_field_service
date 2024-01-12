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
    nombre_del_solicitante = fields.Char(string="Nombre del solicitante", related="helpdesk_ticket_id.nombre_del_solicitante")
    clinica_solicitante = fields.Selection("Clinica solicitante", related="helpdesk_ticket_id.clinica_solicitante")
    timeline_ids = fields.One2many('project.timeline.mod','timeline_project_id')
    partner_phone2 = fields.Char(string="Telefono 2?", related="helpdesk_ticket_id.phone2")
    pilot_name = fields.Char(string="Nombre del piloto")
    circuit = fields.Char(string="Circuito")
    dpi_number = fields.Char(string="DPI", related="partner_id.dpi_number", readonly=False)
    ticket_service_id = fields.Many2one("helpdesk.ticket", string="Ticket de servicio de asistencia")
    phone2 = fields.Char(string="Teléfono 2", related="helpdesk_ticket_id.phone2")
    amount = fields.Float(string="Total de la factura", related="helpdesk_ticket_id.amount")
    street_dispach = fields.Char(string="Dirección de despacho", related="helpdesk_ticket_id.street_dispach")
    who_receives = fields.Char(string="Nombre de quien recibe", related="helpdesk_ticket_id.who_receives")
    general_delivery_remarks = fields.Char(string="Observaciones generales para entrega", related="helpdesk_ticket_id.general_delivery_remarks")
    date_delivery = fields.Date(string="Fecha solicitada de entrega", related="helpdesk_ticket_id.date_delivery")
    assigned_today = fields.Selection([('Si', 'Si'), ('No', 'No')], string="Asignado para hoy", related="helpdesk_ticket_id.assigned_today") 
    payment_way = fields.Selection([
        ('Efectivo', 'Efectivo contra entrega'),
        ('Tarjeta', 'Tarjeta/POS'),
        ('Visalink', 'Visalink'),
        ('Cancelado', 'Cancelado'),
        ('Solo para asignar NO UTILIZAR','Solo para asignar NO UTILIZAR')
    ], string="Forma de Pago", related="helpdesk_ticket_id.payment_way")
    clinica_solicitante = fields.Selection(
        [('CONDADO', 'CONDADO'),
         ('MAJADAS', 'MAJADAS'),
         ('AMÉRICAS', 'AMÉRICAS'),
         ('XPO1', 'XPO1'),
         ('FRUTAL', 'FRUTAL'),
         ('PORTALES', 'PORTALES'),
         ('SAN CRISTOBAL', 'SAN CRISTOBAL'),
         ('BLUEMEDS', 'BLUEMEDS'),
         ('DELIVERY CAS', 'DELIVERY CAS'),
         ('DESPACHO', 'DESPACHO')],
        string="Área solicitante", related="helpdesk_ticket_id.clinica_solicitante")
    
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
                'piloto':a.pilot_name,
                'circuito': a.circuit,
                'partner_id': a.partner_id.id,
                'stage_id': a.stage_id.id,
                'template_work_id': a.worksheet_template_id.id,
                'dpi': a.dpi_number,
                'tel': a.partner_phone,
                'tel_2': a.partner_phone2,
                'forma_pago': a.payment_way,
                'monto': a.amount,
                'direccion_d': a.street_dispach,
                'observacion': a.general_delivery_remarks,
                'articulo_venta': a.sale_line_id.id,
                'ticket_servicio': a.ticket_service_id.id,
            }
        self.timeline_ids.create(vals_list)


class helpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"
    
    create_uid = fields.Many2one('res.users', readonly=False, store=True, copied=False)
    partner_name = fields.Char(string="Cliente")
    timeline_help_ids = fields.One2many('helpdesk.timeline.mod','timeline_help_id')
    team_new = fields.Char()
    team_old = fields.Char()
    insurance_carrier_id = fields.Many2one('xmart.hospital', string="Aseguradora", store=True)
    nombre_del_solicitante = fields.Char(string="Nombre de solicitante")
    clinica_solicitante = fields.Selection(
        [('CONDADO', 'CONDADO'),
         ('MAJADAS', 'MAJADAS'),
         ('AMÉRICAS', 'AMÉRICAS'),
         ('XPO1', 'XPO1'),
         ('FRUTAL', 'FRUTAL'),
         ('PORTALES', 'PORTALES'),
         ('SAN CRISTOBAL', 'SAN CRISTOBAL'),
         ('BLUEMEDS', 'BLUEMEDS'),
         ('DELIVERY CAS', 'DELIVERY CAS'),
         ('DESPACHO', 'DESPACHO')],
        string="Área solicitante")
    birthdate = fields.Date(string="Fecha de nacimiento", store=True)
    dpi_number = fields.Char(string="DPI", store=True)
    phone = fields.Char(string="Teléfono", store=True)
    email = fields.Char(string="Correo Electrónico", store=True)
    ticket_number = fields.Char(string="Boleta/Token", store=True)
    bluemeds_id = fields.Char(string="Personal ID (Bluemeds)")
    welcome_bluemeds = fields.Selection([('Si', 'Si'), ('No', 'No')], string="Requiere kit de bienvenida (Bluemeds)") 
    no_affilition = fields.Char(string="Afiliación")
    no_carnet = fields.Char(string="Núm. de carnet de seguro")
    doctor_internal = fields.Char(string="Doctor interno")
    doctor_external = fields.Char(string="Doctor Externo")
    form = fields.Selection([('Si', 'Si'), ('No', 'No')], string="Cuenta con formulario de autorización") 
    prescription = fields.Selection([('Si', 'Si'), ('No', 'No')], string="Cuenta con receta medica") 
    telemedicine = fields.Selection([('Si', 'Si'), ('No', 'No')], string="Telemedicina") 
    phone2 = fields.Char(string="Teléfono 2")
    amount = fields.Float(string="Total de la factura")
    street_dispach = fields.Char(string="Dirección de despacho")
    who_receives = fields.Char(string="Nombre de quien recibe")
    general_delivery_remarks = fields.Char(string="Observaciones generales para entrega")
    date_delivery = fields.Date(string="Fecha solicitada de entrega")
    assigned_today = fields.Selection([('Si', 'Si'), ('No', 'No')], string="Asignado para hoy") 
    payment_way = fields.Selection([
        ('Efectivo', 'Efectivo contra entrega'),
        ('Tarjeta', 'Tarjeta/POS'),
        ('Visalink', 'Visalink'),
        ('Cancelado', 'Cancelado'),
        ('Solo para asignar NO UTILIZAR','Solo para asignar NO UTILIZAR')
    ], string="Forma de Pago")
    department_id = fields.Many2one("res.country.state", string="Departamento")
    municipality_id = fields.Many2one("res.country.municipality", string="Municipio")
    zone = fields.Char(string="Zona", store=True)
    vat = fields.Char(string="NIT para facturación", store=True)
    name_to_invoice = fields.Char(string="Nombre de a quien se factura")
    street_to_invoice = fields.Char(string="Dirección de facturación")
    amount_change = fields.Char(string="Pago efectivo, especificar si necesita vuelto")
    cc_email = fields.Char(string="CC del correo electrónico")
    order_id = fields.Char(string="Orden ID")
    type_order = fields.Selection([('Supervisar', 'Supervisar'), ('Cobros en cola', 'Cobros en cola')], string="Tipo de orden")
    amount_total_invoice = fields.Float(string="Monto total Orden")
    amount_total_paid = fields.Float(string="Monto total cobrado")
    assigned_priority = fields.Selection([('Prioridad para cabina de seguros', 'Prioridad para cabina de seguros')], string="Asignación prioritaria en clínica")

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
            'assigned_today': self.asignado,
        }
        
    
class helpdeskTimeline(models.Model):
    _name = "helpdesk.timeline.mod"
    
    timeline_help_id = fields.Many2one('helpdesk.ticket')
    department_id = fields.Many2one('res.country.state', related='timeline_help_id.department_id', string="Departamento")
    municipality_id = fields.Many2one('x_res_municipality', related='timeline_help_id.municipality_id', string="Municipio")
    zone_id = fields.Char(string="Zona")
    area_solicitant = fields.Selection(string='Area solicitante', related='timeline_help_id.clinica_solicitante')
    name_solicitant = fields.Char(string='Nombre solicitante', related='timeline_help_id.nombre_del_solicitante')
    partner_id = fields.Many2one("res.partner", string="Cliente", related='timeline_help_id.partner_id')
    request_delivery_date = fields.Date(string='Fecha solicitada de entrega', related='timeline_help_id.date_delivery')
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
    asignado_hoy = fields.Selection(string='Asignado para hoy', related='timeline_project_id.assigned_today')
    fecha_entrega = fields.Date(string='Fecha solicitada de entrega', related='timeline_project_id.date_delivery')
    articulo_venta = fields.Many2one('sale.order.line', string='Articulo en la orden de venta')
    etiqueta = fields.Many2many('project.tags',related='timeline_project_id.tag_ids',string='Etiquetas')
    ticket_servicio = fields.Many2one('helpdesk.ticket', related='timeline_project_id.ticket_service_id',string='Ticket se servicio de asistencia')