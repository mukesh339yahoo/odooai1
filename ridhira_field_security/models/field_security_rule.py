from odoo import models, fields, api
from odoo.exceptions import ValidationError

class FieldSecurityRule(models.Model):
    _name = 'field.security.rule'
    _description = 'Field & UI Security Rule'
    _order = 'sequence, id'

    name = fields.Char(string='Rule Name', compute='_compute_name', store=True, readonly=False)
    sequence = fields.Integer(string='Priority', default=10, help="Lower sequence rules are evaluated first.")
    
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade')
    target_type = fields.Selection([
        ('field', 'Field'),
        ('button', 'Button / Action'),
        ('page', 'Notebook Tab / Page')
    ], string='Target Type', required=True, default='field')
    
    field_id = fields.Many2one('ir.model.fields', string='Field', ondelete='cascade',
                               domain="[('model_id', '=', model_id)]")
    button_name = fields.Char(string='Button Name (name attribute)', help="e.g., action_confirm")
    page_name = fields.Char(string='Tab / Page Name or Title', help="Technical name (name='...') or visible label (string='...') of the tab/page to hide")
    
    apply_behavior = fields.Selection([
        ('include', 'Apply To Selected'),
        ('exclude', 'Apply To All EXCEPT Selected')
    ], string='Apply Behavior', required=True, default='include')
    
    group_ids = fields.Many2many('res.groups', string='User Groups')
    user_ids = fields.Many2many('res.users', string='Specific Users')
    company_id = fields.Many2one('res.company', string='Company', help="Leave blank to apply across all companies")
    
    view_type = fields.Selection([
        ('all', 'All Views'),
        ('form', 'Form View Only'),
        ('list', 'List View Only'),
        ('tree', 'List View Only (Legacy)')
    ], string='Apply to View', required=True, default='all')
    
    rule_type = fields.Selection([
        ('invisible', 'Invisible (Hide)'),
        ('readonly', 'Read-Only'),
        ('required', 'Required (Mandatory)'),
        ('no_export', 'Prevent Export (Excel/CSV)'),
        ('mask', 'Mask Confidential Data')
    ], string='Rule Type', required=True, default='invisible')
    
    masking_pattern = fields.Selection([
        ('all', 'Full Mask (********)'),
        ('partial_end', 'Show Last 4 Characters (**** 1234)'),
        ('partial_start', 'Show First 4 Characters (1234 ****)')
    ], string='Masking Pattern', default='all', help="Format used when masking sensitive data.")
    
    enforce_backend = fields.Boolean(
        string='Enforce Server-Side Write Protection',
        default=True,
        help="Block unauthorized write, create, and import operations at the ORM level, preventing developer mode or API bypass."
    )
    
    domain = fields.Char(string='Condition (Domain / Expression)', help="e.g., state == 'done' or [('state', '=', 'done')]")
    active = fields.Boolean(default=True, string='Active')

    @api.depends('target_type', 'field_id', 'button_name', 'page_name', 'model_id', 'rule_type')
    def _compute_name(self):
        for rec in self:
            if rec.name:
                continue
            action = dict(rec._fields['rule_type'].selection).get(rec.rule_type, rec.rule_type or 'Rule')
            target = ""
            if rec.target_type == 'field' and rec.field_id:
                target = f"Field '{rec.field_id.field_description or rec.field_id.name}'"
            elif rec.target_type == 'button':
                target = f"Button '{rec.button_name or ''}'"
            elif rec.target_type == 'page':
                target = f"Tab '{rec.page_name or ''}'"
            else:
                target = "Element"
            model_name = rec.model_id.name or (rec.model_id.model if rec.model_id else '')
            rec.name = f"{action} {target} on {model_name}".strip()

    # Odoo 19 & 20 models.Constraint with backward compatibility fallback
    if hasattr(models, 'Constraint'):
        _target_required_field = models.Constraint(
            "CHECK((target_type='field' AND field_id IS NOT NULL) OR (target_type != 'field'))",
            'Field is required when target type is Field.'
        )
        _target_required_button = models.Constraint(
            "CHECK((target_type='button' AND button_name IS NOT NULL) OR (target_type != 'button'))",
            'Button Name is required when target type is Button.'
        )
        _target_required_page = models.Constraint(
            "CHECK((target_type='page' AND page_name IS NOT NULL) OR (target_type != 'page'))",
            'Tab / Page Name is required when target type is Tab / Page.'
        )
    else:
        _sql_constraints = [
            ('target_required_field', "CHECK((target_type='field' AND field_id IS NOT NULL) OR (target_type != 'field'))", 'Field is required when target type is Field.'),
            ('target_required_button', "CHECK((target_type='button' AND button_name IS NOT NULL) OR (target_type != 'button'))", 'Button Name is required when target type is Button.'),
            ('target_required_page', "CHECK((target_type='page' AND page_name IS NOT NULL) OR (target_type != 'page'))", 'Tab / Page Name is required when target type is Tab / Page.')
        ]

    @api.constrains('target_type', 'field_id', 'button_name', 'page_name')
    def _check_target(self):
        for record in self:
            if record.target_type == 'field' and not record.field_id:
                raise ValidationError("Field is required when target type is Field.")
            if record.target_type == 'button' and not record.button_name:
                raise ValidationError("Button Name is required when target type is Button.")
            if record.target_type == 'page' and not record.page_name:
                raise ValidationError("Tab / Page Name is required when target type is Notebook Tab / Page.")
