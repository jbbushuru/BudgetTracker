from django.apps import AppConfig


class FinanceConfig(AppConfig):
    name = 'Finance'
    #logic for seeding categories
    def ready(self):
        print("Finance app ready logic executing...")
        # 1. Connect to post_migrate for seeding after migrations
        from django.db.models.signals import post_migrate
        post_migrate.connect(self.run_seed_categories, sender=self)
        
        # 2. Also attempt to seed immediately on startup (for regular restarts)
        import sys
        if 'runserver' in sys.argv:
            try:
                self.seed_categories()
            except Exception as e:
                print(f"Initial category seeding skipped: {e}")

    def run_seed_categories(self, **kwargs):
        """
        Wrapper for post_migrate signal to trigger seeding.
        """
        print("Running category seeding via post_migrate...")
        try:
            self.seed_categories()
        except Exception as e:
            print(f"Error during category seeding: {e}")

    def seed_categories(self):
        from .models import Category
        categories = [
            { "name": "Education", "icon_name": "school", "color_code": "#FFD93D", "is_essential": True },
            { "name": "Entertainment", "icon_name": "film", "color_code": "#9B59B6", "is_essential": False },
            { "name": "Food & Dining", "icon_name": "restaurant", "color_code": "#E74C3C", "is_essential": True },
            { "name": "Healthcare", "icon_name": "medkit", "color_code": "#4ECDC4", "is_essential": True },
            { "name": "Other Expense", "icon_name": "ellipsis-horizontal", "color_code": "#94A3B8", "is_essential": False },
            { "name": "Shopping", "icon_name": "cart", "color_code": "#F39C12", "is_essential": False },
            { "name": "Transportation", "icon_name": "car", "color_code": "#3498DB", "is_essential": True },
            { "name": "Travel", "icon_name": "airplane", "color_code": "#6B46C1", "is_essential": False },
            { "name": "Utilities", "icon_name": "flash", "color_code": "#FF8F5E", "is_essential": True },
            #added new categories
            { "name": "Transaction Costs", "icon_name": "currency-exchange", "color_code": "#D32F2F", "is_essential": True },
            { "name": "Savings", "icon_name": "wallet", "color_code": "#2ECC71", "is_essential": True },
            { "name": "Data & Airtime", "icon_name": "phone-portrait", "color_code": "#00A8FF", "is_essential": True },
            { "name": "MPesa Reversal", "icon_name": "refresh-circle", "color_code": "#7F8C8D", "is_essential": False },
            { "name": "MPesa Withdrawal", "icon_name": "arrow-up-circle", "color_code": "#C0392B", "is_essential": True },
            { "name": "MPesa Deposit", "icon_name": "arrow-down-circle", "color_code": "#27AE60", "is_essential": True }
        ]
        
        for cat_data in categories:
            Category.objects.update_or_create(
                name=cat_data['name'],
                defaults={
                    'icon_name': cat_data['icon_name'],
                    'color_code': cat_data['color_code'],
                    'is_essential': cat_data['is_essential'],
                    'owner': None,
                }
            )
        print("System categories seeded/updated successfully.")
