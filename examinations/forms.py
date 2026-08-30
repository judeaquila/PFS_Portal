from django import forms
from .models import Question, Exam

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['exam', 'category', 'text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer', 'is_active']
        
        input_attrs = {
            'class': 'w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-pink-500 transition'
        }
        
        widgets = {
            'exam': forms.Select(attrs=input_attrs),
            'category': forms.Select(attrs=input_attrs),
            'text': forms.Textarea(attrs={**input_attrs, 'rows': 3, 'placeholder': 'Enter question statement...'}),
            'option_a': forms.TextInput(attrs={**input_attrs, 'placeholder': 'Option A'}),
            'option_b': forms.TextInput(attrs={**input_attrs, 'placeholder': 'Option B'}),
            'option_c': forms.TextInput(attrs={**input_attrs, 'placeholder': 'Option C'}),
            'option_d': forms.TextInput(attrs={**input_attrs, 'placeholder': 'Option D'}),
            'correct_answer': forms.Select(attrs=input_attrs),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 rounded bg-slate-900 border-slate-800 text-pink-600 focus:ring-pink-500 focus:ring-offset-slate-950'
            }),
        }


# class SupervisorQuestionForm(forms.ModelForm):
#     class Meta:
#         model = Question
#         fields = ['category', 'text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer', 'is_active']
        
#         input_classes = "w-full bg-gray-50 border border-gray-300 text-gray-900 text-xs rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 p-3 transition"
        
#         widgets = {
#             'category': forms.Select(attrs={'class': input_classes}),
#             'text': forms.Textarea(attrs={'class': input_classes, 'rows': 3}),
#             'option_a': forms.TextInput(attrs={'class': input_classes}),
#             'option_b': forms.TextInput(attrs={'class': input_classes}),
#             'option_c': forms.TextInput(attrs={'class': input_classes}),
#             'option_d': forms.TextInput(attrs={'class': input_classes}),
#             'correct_answer': forms.Select(attrs={'class': input_classes}),
#             'is_active': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-indigo-600 bg-gray-100 border-gray-300 rounded focus:ring-indigo-500'}),
#         }


# from django import forms
# from .models import Exam, Question

class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-xs text-gray-900 placeholder-gray-400 transition',
                'placeholder': 'e.g., Q3 Associate Compliance Certification'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-xs text-gray-900 placeholder-gray-400 transition',
                'rows': 4,
                'placeholder': 'Provide a brief summary or guidelines for this exam...'
            }),
        }


class SupervisorQuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['category', 'text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer', 'is_active']
        widgets = {
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-xs text-gray-900 transition'
            }),
            'text': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-xs text-gray-900 transition',
                'rows': 3,
                'placeholder': 'Enter the question text here...'
            }),
            'option_a': forms.TextInput(attrs={
                'class': 'w-full px-3.5 py-2 rounded-xl border border-gray-300 focus:ring-2 focus:ring-indigo-500 text-xs text-gray-900 transition',
                'placeholder': 'Option A'
            }),
            'option_b': forms.TextInput(attrs={
                'class': 'w-full px-3.5 py-2 rounded-xl border border-gray-300 focus:ring-2 focus:ring-indigo-500 text-xs text-gray-900 transition',
                'placeholder': 'Option B'
            }),
            'option_c': forms.TextInput(attrs={
                'class': 'w-full px-3.5 py-2 rounded-xl border border-gray-300 focus:ring-2 focus:ring-indigo-500 text-xs text-gray-900 transition',
                'placeholder': 'Option C'
            }),
            'option_d': forms.TextInput(attrs={
                'class': 'w-full px-3.5 py-2 rounded-xl border border-gray-300 focus:ring-2 focus:ring-indigo-500 text-xs text-gray-900 transition',
                'placeholder': 'Option D'
            }),
            'correct_answer': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-xs text-gray-900 transition'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500 transition cursor-pointer'
            }),
        }