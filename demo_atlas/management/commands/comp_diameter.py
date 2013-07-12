from gstudio.models import *
from django.core.management.base import BaseCommand
import settings
from graph_methods.localMethods import computeDiameter


class Command(BaseCommand):
	def handle(self,*args,**options):		
               
    		computeDiameter()

