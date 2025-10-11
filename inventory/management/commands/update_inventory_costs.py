from django.core.management.base import BaseCommand
from inventory.models import InventoryMovement

class Command(BaseCommand):
    help = 'تحديث التكلفة الإجمالية لحركات المخزون'

    def handle(self, *args, **options):
        movements = InventoryMovement.objects.all()
        updated_count = 0
        
        for movement in movements:
            old_total = movement.total_cost
            movement.total_cost = movement.quantity * movement.unit_cost
            if old_total != movement.total_cost:
                movement.save(update_fields=['total_cost'])
                updated_count += 1
                self.stdout.write(f'تم تحديث حركة {movement.movement_number}: {old_total} -> {movement.total_cost}')
        
        self.stdout.write(
            self.style.SUCCESS(f'تم تحديث {updated_count} حركة مخزون')
        )