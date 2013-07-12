from gstudio.models import *
from django.core.management.base import BaseCommand
import settings
from graph_methods.localMethods import generate_local_instance


class Command(BaseCommand):
	def handle(self,*args,**options):		
               
    		generate_local_instance()

