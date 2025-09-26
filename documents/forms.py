from django import forms
from .models import Document

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['title', 'file']
        labels = {
            'title': 'عنوان المستند',
            'file': 'الملف',
        }