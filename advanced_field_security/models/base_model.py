import logging
from lxml import etree
from odoo import models, api

_logger = logging.getLogger(__name__)

class BaseModel(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _apply_field_security_rules_to_arch(self, arch_node, view_type):
        if self.env.is_superuser():
            return

        rules = self.env['field.security.rule'].sudo().search([
            ('model_id.model', '=', self._name)
        ])

        if not rules:
            return

        user = self.env.user
        user_groups = user.groups_id
        
        applied_rules = []
        for rule in rules:
            # Check View Type Granularity
            if rule.view_type != 'all' and rule.view_type != view_type:
                continue
                
            # Check User/Group logic
            match = False
            if user in rule.user_ids or any(g in user_groups for g in rule.group_ids):
                match = True
                
            if rule.apply_behavior == 'include' and match:
                applied_rules.append(rule)
            elif rule.apply_behavior == 'exclude' and not match:
                applied_rules.append(rule)

        if not applied_rules:
            return

        rules_by_field = {}
        rules_by_button = {}
        
        for rule in applied_rules:
            if rule.target_type == 'field' and rule.field_id:
                if rule.field_id.name not in rules_by_field:
                    rules_by_field[rule.field_id.name] = []
                rules_by_field[rule.field_id.name].append(rule)
            elif rule.target_type == 'button' and rule.button_name:
                if rule.button_name not in rules_by_button:
                    rules_by_button[rule.button_name] = []
                rules_by_button[rule.button_name].append(rule)

        # Apply to fields
        for node in arch_node.xpath('//field'):
            field_name = node.get('name')
            if field_name in rules_by_field:
                for rule in rules_by_field[field_name]:
                    self._inject_rule_modifier(node, rule)
                    
        # Apply to buttons
        for node in arch_node.xpath('//button'):
            button_name = node.get('name')
            if button_name in rules_by_button:
                for rule in rules_by_button[button_name]:
                    self._inject_rule_modifier(node, rule)

    def _inject_rule_modifier(self, node, rule):
        modifier = rule.rule_type
        if modifier == 'no_export':
            return
            
        value = rule.domain or '1'
        node.set(modifier, value)
        
        if modifier == 'readonly' and node.get('force_save') is None:
            node.set('force_save', '1')

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
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
        res = super(BaseModel, self).fields_get(allfields=allfields, attributes=attributes)
        
        if self.env.is_superuser():
            return res

        rules = self.env['field.security.rule'].sudo().search([
            ('model_id.model', '=', self._name),
            ('target_type', '=', 'field')
        ])
        
        if not rules:
            return res

        user = self.env.user
        user_groups = user.groups_id
        
        for rule in rules:
            match = False
            if user in rule.user_ids or any(g in user_groups for g in rule.group_ids):
                match = True
                
            applies = (rule.apply_behavior == 'include' and match) or (rule.apply_behavior == 'exclude' and not match)
            
            if applies:
                field_name = rule.field_id.name
                if field_name in res:
                    if rule.rule_type == 'invisible' and not rule.domain:
                        res.pop(field_name, None)
                    elif rule.rule_type == 'readonly' and not rule.domain:
                        res[field_name]['readonly'] = True
                    elif rule.rule_type == 'required' and not rule.domain:
                        res[field_name]['required'] = True
                    elif rule.rule_type == 'no_export':
                        res[field_name]['exportable'] = False
                        
        return res
