from odoo import models, fields, api

class FieldSecurityRule(models.Model):
    _name = 'field.security.rule'
    _description = 'Field & UI Security Rule'

    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade')
    target_type = fields.Selection([
        ('field', 'Field'),
        ('button', 'Button / Action')
    ], string='Target Type', required=True, default='field')
    
    field_id = fields.Many2one('ir.model.fields', string='Field', ondelete='cascade',
                               domain="[('model_id', '=', model_id)]")
    button_name = fields.Char(string='Button Name (name attribute)', help="e.g., action_confirm")
    
    apply_behavior = fields.Selection([
        ('include', 'Apply To Selected'),
        ('exclude', 'Apply To All EXCEPT Selected')
    ], string='Apply Behavior', required=True, default='include')
    
    group_ids = fields.Many2many('res.groups', string='User Groups')
    user_ids = fields.Many2many('res.users', string='Specific Users')
    
    view_type = fields.Selection([
        ('all', 'All Views'),
        ('form', 'Form View Only'),
        ('tree', 'Tree/List View Only')
    ], string='Apply to View', required=True, default='all')
    
    rule_type = fields.Selection([
        ('invisible', 'Invisible'),
        ('readonly', 'Read-Only'),
        ('required', 'Required'),
        ('no_export', 'Prevent Export')
    ], string='Rule Type', required=True, default='invisible')
    
    domain = fields.Char(string='Condition (Domain)', help="e.g., [('state', '=', 'done')]")
    active = fields.Boolean(default=True, string='Active')

    _sql_constraints = [
        ('target_required_field', "CHECK((target_type='field' AND field_id IS NOT NULL) OR (target_type='button'))", 'Field is required when target type is Field.'),
        ('target_required_button', "CHECK((target_type='button' AND button_name IS NOT NULL) OR (target_type='field'))", 'Button Name is required when target type is Button.')
    ]
