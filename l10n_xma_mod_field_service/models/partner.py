from odoo import api, fields, models, SUPERUSER_ID, _

class ProjectTask(models.Model):
    _inherit = "res.partner"

    municipality_id = fields.Many2one("res.country.municipality", string="Municipio")
    zone = fields.Char(string="Zona")

class Municipality(models.Model):
    _name = "res.country.municipality"
    name  = fields.Char(string="Nombre")
    code  = fields.Char(string="Codigo")
    state_id  = fields.Many2one("res.country.state", string="Estado")
    