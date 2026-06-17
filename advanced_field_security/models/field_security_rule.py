from odoo import models, fields, api

class FieldSecurityRule(models.Model):
    _name = 'field.security.rule'
    _description = 'Field Security Rule'

    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade')
    field_id = fields.Many2one('ir.model.fields', string='Field', required=True, ondelete='cascade',
                               domain="[('model_id', '=', model_id)]")
    group_ids = fields.Many2many('res.groups', string='User Groups', required=True)
    rule_type = fields.Selection([
        ('invisible', 'Invisible'),
        ('readonly', 'Read-Only'),
        ('required', 'Required')
    ], string='Rule Type', required=True, default='invisible')
    active = fields.Boolean(default=True, string='Active')

    _sql_constraints = [
        ('model_field_rule_uniq', 'unique (model_id, field_id, rule_type)',
         'A rule type for this field and model already exists!')
    ]
