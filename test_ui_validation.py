import os
import sys
import django

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(__file__))

# Setup Django before any imports
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth.models import User
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time

class AttendancePageTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Create test user if not exists
        if not User.objects.filter(username='test').exists():
            User.objects.create_user(username='test', password='testadmin1234')

    def test_attendance_page_content(self):
        """Test that attendance page displays correct content without mixed text"""
        # Login
        self.client.login(username='test', password='testadmin1234')

        # Get the page
        response = self.client.get('/en/hr/attendance/46/')
        self.assertEqual(response.status_code, 200)

        # Check that the page contains the correct English text
        content = response.content.decode('utf-8')
        print("Page content preview:")
        print(content[:2000])  # First 2000 chars

        # Check for the correct text
        self.assertIn('Normal work + two additional hours.', content)
        self.assertNotIn('دوام طبيعي + ساعتين إضاIn.', content)

        print("✓ Database content is correct")
        print("✓ Page loads successfully")

    def test_selenium_ui_check(self):
        """Use Selenium to check the actual rendered content in browser"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        try:
            # Navigate to the page
            driver.get('http://127.0.0.1:8000/en/hr/attendance/46/')

            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Get the rendered text
            body_text = driver.find_element(By.TAG_NAME, "body").text
            print("Rendered page text:")
            print(body_text[:1000])

            # Check for correct content
            if 'Normal work + two additional hours.' in body_text:
                print("✓ Correct English text found in rendered content")
            else:
                print("✗ Correct English text NOT found in rendered content")

            if 'دوام طبيعي' in body_text:
                print("✗ Arabic text still present in rendered content")
            else:
                print("✓ No Arabic text found in rendered content")

        finally:
            driver.quit()

if __name__ == '__main__':
    import unittest
    unittest.main()