import logging
import os
import textwrap

import hjson
from django.core.management.base import BaseCommand

from biostar.engine import auth
from biostar.engine.models import Project, Analysis

logger = logging.getLogger('engine')

__CURR_DIR = os.path.dirname(os.path.realpath(__file__))


class Command(BaseCommand):
    help = 'Manages analyses.'

    def add_arguments(self, parser):

        parser.add_argument('--add', action='store_true', default=False,
                            help="Adds an analysis to a project")

        parser.add_argument('--id', default=1,
                            help="Specifies the project id")

        parser.add_argument('--json',
                            help="The json specification file")

        parser.add_argument('--template',
                            help="The template for the analysis")

        parser.add_argument('--jobs', action='store_true', default=False,
                            help="Also creates a queued job for the analysis")

    def handle(self, *args, **options):

        json = options['json']
        pid = options['id']
        template_fname = options['template']
        jobs = options['jobs']

        verbosity = int(options['verbosity'])

        if verbosity > 1:
            logger.setLevel(logging.DEBUG)
            logger.info(f"level={verbosity}")

        # Require JSON and templatates to exist.
        if not (json and template_fname):
            logger.error("This command requires --json and a --template to be set")
            return

        # Get the target project.
        project = Project.objects.filter(id=pid).first()

        # Invalid project specified.
        if not project:
            logger.error(f'No project with id={pid}')
            return

        # JSON file does not exist.
        if not os.path.isfile(json):
            logger.error(f'No file found for --json={json}')
            return

        # Template file does not exist.
        if not os.path.isfile(template_fname):
            logger.error(f'No file found for --template={template}')
            return

        try:
            # Parse the json_text into json_data
            json_text = open(json).read()
            json_path = os.path.dirname(json)
            json_data = hjson.loads(json_text)
        except Exception as exc:
            logger.exception(f"JSON exception in file: {json}\n{exc}")
            return

        try:
            # Read the specification
            template = open(template_fname).read()
        except Exception as exc:
            logger.exception(f"Template exception: {exc}")
            return

        try:
            name = json_data.get("settings", {}).get("name", "No name")
            text = json_data.get("settings", {}).get("help", "No help")
            uid = json_data.get("settings", {}).get("uid", "")
            image = json_data.get("settings", {}).get("image", "")
            text = textwrap.dedent(text)
            summary = json_data.get("settings", {}).get("summary", "No summary")

            # Create the analysis
            analysis = auth.create_analysis(project=project, uid=uid, json_text=json_text, summary=summary,
                                            template=template, name=name, text=text, security=Analysis.AUTHORIZED)

            # Load the image if specified.
            if image:
                image_path = os.path.join(json_path, image)
                if os.path.isfile(image_path):
                    stream = open(image_path, 'rb')
                    analysis.image.save(image, stream, save=True)
                    logger.info(f"Image path: {image_path}")
                else:
                    logger.error(f"Skipping invalid image path: {image_path}")

            # Create a queued jobs if instructed so.
            if jobs:

                # Deposit the files specified with the analysis.
                for key, obj in json_data.items():

                    # Data that comes from the project.
                    is_project_data = (obj.get("source") == "PROJECT")

                    # Get next field if this is not data.
                    if not is_project_data:
                        continue

                    # Parameters need to have a value with a test file.
                    value = obj.get("value", "")

                    if not value:
                        logger.warning(f"In template={template_fname} data key={key} does not have a 'value' attribute.")
                        continue

                    # Get the various data attributes.
                    summary = obj.get("summary", "")
                    text = obj.get("text", "")
                    data_type = obj.get("type", "")
                    name = obj.get("name", "") or os.path.basename(value)

                    # Create the data entry.
                    data = auth.create_data(project=project, name=name, path=value, data_type=data_type,
                                            summary=summary, text=text)

                    # Mutate the object in the json_data contain the current dataset.
                    data.fill_dict(obj)

                    # Create the job.
                    auth.create_job(analysis=analysis, json_data=json_data)

        except Exception as exc:
            logger.exception(f"Error: {exc}")
            return
