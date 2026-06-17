import logging
from lxml import etree
from odoo import models, api

_logger = logging.getLogger(__name__)

class BaseModel(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _apply_field_security_rules_to_arch(self, arch_node, view_type):
        """
        Parses the view architecture and applies field security rules.
        """
        # Skip if superuser
        if self.env.is_superuser():
            return

        # Fetch active rules for the current model
        rules = self.env['field.security.rule'].sudo().search([
            ('model_id.model', '=', self._name)
        ])

        if not rules:
            return

        # Check which rules apply to the current user
        user_groups = self.env.user.groups_id
        applied_rules = []
        for rule in rules:
            if any(g in user_groups for g in rule.group_ids):
                applied_rules.append(rule)

        if not applied_rules:
            return

        # Group rules by field name
        rules_by_field = {}
        for rule in applied_rules:
            field_name = rule.field_id.name
            if field_name not in rules_by_field:
                rules_by_field[field_name] = []
            rules_by_field[field_name].append(rule.rule_type)

        # Iterate over all field nodes in the view
        for node in arch_node.xpath('//field'):
            field_name = node.get('name')
            if field_name in rules_by_field:
                rule_types = rules_by_field[field_name]
                
                # Apply rules
                if 'invisible' in rule_types:
                    node.set('invisible', '1')
                
                if 'readonly' in rule_types:
                    # In Odoo 17+, readonly modifier is directly on the node or in modifiers
                    node.set('readonly', '1')
                    if node.get('force_save') is None:
                        node.set('force_save', '1')
                        
                if 'required' in rule_types:
                    node.set('required', '1')

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        """
        Override get_view to intercept the arch and apply security rules.
        """
        res = super(BaseModel, self).get_view(view_id=view_id, view_type=view_type, **options)
        
        try:
            arch_node = etree.fromstring(res['arch'])
            self._apply_field_security_rules_to_arch(arch_node, view_type)
            res['arch'] = etree.tostring(arch_node, encoding='unicode')
        except Exception as e:
            _logger.error("Failed to apply field security rules on %s: %s", self._name, e)
            
        return res

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """
        Override fields_get to enforce invisible rules at the field level,
        preventing RPC field discovery and export.
        """
        res = super(BaseModel, self).fields_get(allfields=allfields, attributes=attributes)
        
        if self.env.is_superuser():
            return res

        rules = self.env['field.security.rule'].sudo().search([
            ('model_id.model', '=', self._name)
        ])
        
        if not rules:
            return res

        user_groups = self.env.user.groups_id
        for rule in rules:
            if any(g in user_groups for g in rule.group_ids):
                field_name = rule.field_id.name
                if field_name in res:
                    if rule.rule_type == 'invisible':
                        res.pop(field_name, None)
                    elif rule.rule_type == 'readonly':
                        res[field_name]['readonly'] = True
                    elif rule.rule_type == 'required':
                        res[field_name]['required'] = True
                        
        return res
