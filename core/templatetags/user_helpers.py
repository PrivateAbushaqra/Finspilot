from django import template

register = template.Library()

@register.simple_tag
def should_show_sidebar(user):
    """
    يحدد ما إذا كان يجب إظهار القائمة الجانبية للمستخدم
    القائمة تظهر لكل المستخدمين except pos_user الذين ليسوا في مجموعات
    """
    if not user.is_authenticated:
        return False
    
    # إذا لم يكن pos_user، أظهر القائمة
    if not hasattr(user, 'user_type') or user.user_type != 'pos_user':
        return True
    
    # إذا كان pos_user في مجموعة، أظهر القائمة
    if user.groups.exists():
        return True
    
    # pos_user بدون مجموعات، لا تظهر القائمة
    return False
