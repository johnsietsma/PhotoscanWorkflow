
import PhotoScan
import datetime
import glob
import os

'''
A workflow to process multiple set of photos in Photoscan.

Expects a directory structure like this:
<HomeDirectory>
	Directory1
		<PhotosDirectory>
			photo1.tif
			photo2.tif
	Directory2
		<PhotosDirectory>
			photo1.tif
			photo2.tif		

It will put a PhotoScan project file in the base of each directory named <directory>.psz.
All the photos from the <PhotosPdirectory> will be added to the project.

The workflow produces an fbx and texture for each directory, which will be placed in the export directory.

This script can be run multiple times to continue processing after a crashed or cancelled processing run. It
will skip stages that have already been completed.

'''

## Configuration

HomeDirectory = "E:\\Captures"
PhotosDirectory = "Photos"
ExportDirectory = "Export"

match_photos_config = {
	'accuracy': PhotoScan.HighAccuracy,
	'preselection': PhotoScan.GenericPreselection,
}


build_point_cloud_config = {}


build_dense_cloud_config = {
	'quality': PhotoScan.HighQuality
}

build_model_config = {
	'surface': PhotoScan.Arbitrary, 
	'interpolation': PhotoScan.EnabledInterpolation
}

export_model_config = {
	'binary': True,
	'texture_format': "jpg",
	'texture': True, 
	'normals': True, 
	'colors': True,
	'cameras': False,
	'format': "fbx"
}

build_texture_config = {}

#################################################


class WorkflowJob(object):
	def __init__(self, name, precond_func, run_func):
		self.name = name
		self.precond_func = precond_func
		self.run_func = run_func

	def can_run(self, chunk):
		return self.precond_func(chunk)

	def run(self, chunk):
		log( "Running job: " + self.name )
		return self.run_func(chunk)



#################################################
# Logging

log_file = None
def log(msg):
	global log_file
	print(msg)
	if log_file:
		log_file.write(str(msg)+'\n')
		log_file.flush()


def open_log(path):
	global log_file
	log_file = open(os.path.join(path,'workflow.log'), 'w')


def close_log():
	global log_file
	log_file.close()

def log_time():
	log( datetime.datetime.utcnow() )


#################################################
# Utility functions

def does_project_exist(project_dir):
	'Does the PhotoScan project file exist'
	project_name = make_project_filename(project_dir, "psz")
	return glob.glob(project_dir + "\\*.psz")

def are_cameras_aligned(chunk):
	'Assume cameras are aligned if at least one of them have been moved.'
	return len([c for c in chunk.cameras if c.center is not None]) > 0


def export_file_exists(project_directory, format):
	model_name = make_export_filename(project_directory, format)
	return os.path.isfile( model_name )


def is_valid_project_dir( project_dir, photos_dir ):
	"A valid project directory has a photos subdirectory."
	return photos_dir.upper() in (d.upper() for d in os.listdir(project_dir))


def estimate_image_quality(photo):
	return Photoscan.Utils.estimateImageQuality(photo)


def get_export_path(project_dir):
	dir_name = os.path.basename(project_dir)
	return os.path.join(project_dir, ExportDirectory)


def make_project_filename(project_dir, ext):
	'Make a filename in the project directory with the given extension'
	dir_name = os.path.basename(project_dir)
	return os.path.join(project_dir,dir_name + "." + ext);


def make_export_filename(project_dir, ext):
	"Make a filename in the project's export directory"
	dir_name = os.path.basename(project_dir)
	export_path = get_export_path(project_dir)
	return os.path.join(export_path, dir_name + "." + ext);


def export_model(chunk, project_directory, kwargs):
	model_name = make_export_filename(project_directory, kwargs['format'])
	return chunk.exportModel(model_name, **kwargs)


def export_texture(chunk, project_directory):
	texture_name = make_export_filename(project_directory, "jpg")
	return chunk.model.saveTexture(texture_name)


#################################################
# Dumping

def dump_meta(meta, fp):
	if meta and meta.keys:
		fp.write("Meta:\n")
		fp.write(str(meta) + "\n")


def dump_camera_data(cam, fp):
	dump_meta(cam.meta, fp)
	fp.write("Photo Path: " + cam.photo.path + "\n")
	fp.write("Center: " + str(cam.center) + "\n")


def log_chunk_data(chunk):
	log("Number of cameras: {}".format(len(chunk.cameras)))
	log("Cameras are aligned: {}".format(are_cameras_aligned(chunk)))
	log("Has sparse cloud: {}".format(chunk.point_cloud is not None))
	log("Has dense cloud: {}".format(chunk.dense_cloud is not None))
	log("Has model: {}".format(chunk.model is not None))


def dump_chunk_data(chunk, fp):
	fp.write("Number of cameras: {}\n".format(len(chunk.cameras)))
	fp.write("Cameras are aligned: {}\n".format(are_cameras_aligned(chunk)))
	fp.write("Has sparse cloud: {}\n".format(chunk.point_cloud is not None))
	fp.write("Has dense cloud: {}\n".format(chunk.dense_cloud is not None))
	fp.write("Has model: {}\n".format(chunk.model is not None))
	fp.write("Camera offset: loc: {} rot: {}\n".format(chunk.camera_offset.location, chunk.camera_offset.rotation))
	fp.write("Camera accuracy: {}\n".format(chunk.accuracy_cameras))
	fp.write("Markers accuracy: {}\n".format(chunk.accuracy_markers))
	fp.write("Projections accuracy: {}\n".format(chunk.accuracy_projections))
	fp.write("Tie points accuracy: {}\n".format(chunk.accuracy_tiepoints))
	dump_meta(chunk.meta, fp)

	fp.write("Camera Info:\n")
	[dump_camera_data(p, fp) for p in chunk.cameras]


def dump(doc):
	'Write information about the PhotoScan.Document to a file'
	print( "Dumping: " + doc.path)
	fp = open(os.path.join(os.path.dirname(doc.path),'workflow.txt'), 'w')
	dump_meta(doc.meta, fp)
	log_chunk_data(doc.chunk)
	dump_chunk_data(doc.chunk, fp)
	fp.close()


#################################################
# Project functions

def find_project_folders(home_dir, photos_dir):
	'Find all the valid project folders in the home_dir'
	subdirs = os.listdir(home_dir)
	subdirs = [os.path.join(home_dir,sd) for sd in subdirs]
	subdirs = [sd for sd in subdirs if os.path.isdir(sd)]
	subdirs = [sd for sd in subdirs if is_valid_project_dir(sd, photos_dir)]
	return subdirs


def open_project(project_dir):
	log( "Opening project " + project_dir )
	project_name = make_project_filename(project_dir, "psz")
	doc = PhotoScan.Document()
	if not doc.open( project_name ):
		log( "ERROR: Cold not open document: " + project_name)
	return doc


def make_project(project_dir, photos_dir):
	'Make a new project and add the photos from the photos_dir to it.'

	log( "Making project " + project_dir )

	# Create new doc
	doc = PhotoScan.Document()

	# Add the photos to a chunk
	chunk = doc.addChunk()
	photos_dir = os.path.join( project_dir, photos_dir )
	photos = os.listdir(photos_dir)
	photos = [os.path.join(photos_dir,p) for p in photos]
	log( "Found {} photos in {}".format(len(photos), photos_dir))
	if not chunk.addPhotos(photos):
		log( "ERROR: Failed to add photos: " + photos)

	# Save the new project
	project_name = make_project_filename(project_dir, "psz")
	log( "Saving: " + project_name );
	if not doc.save( project_name ):
		log( "ERROR: Failed to save project: " + project_name)

	return doc


def make_or_open_project(project_dir, photos_dir):
	if does_project_exist(project_dir):
		return open_project(project_dir)
	else:
		return make_project(project_dir, photos_dir)



###########################################################################################################


def build(project_dir, photos_dir, jobs):
	log( "Building document: " + project_dir )
	log_time()

	doc = make_or_open_project(project_dir, photos_dir)

	export_path = get_export_path(project_dir)
	if not os.path.exists(export_path):
		os.makedirs(export_path)

	chunk = doc.chunk

	if not chunk:
		log( "ERROR: Chunk is None")
		return False

	if not chunk.enabled:
		log( "Chunk not enabled, skipping" )

	# For use by jobs
	chunk.label = project_dir

	ret = True
	for job in jobs:
		if job.can_run( chunk ):
			if job.run( chunk ):
				log( "Job finished - " + job.name )
				doc.save()
			else:
				log( "ERROR: Job failed - " + job.name )
				ret = False
				break
		else:
			log( "Skipping job " + job.name )


	log( "Finished building chunk" )
	log_time()

	return ret


###########################################################################################################
# Workflow jobs

match_photos_job = WorkflowJob(
		"Match photos",
		lambda chunk: not are_cameras_aligned(chunk),
		lambda chunk: chunk.matchPhotos(**match_photos_config)
	)

align_cameras_job = WorkflowJob(
		"Align Cameras", 
		lambda chunk: not are_cameras_aligned(chunk),
		lambda chunk: chunk.alignCameras
	)

build_point_cloud_job = WorkflowJob(
		"Build point cloud", 
		lambda chunk: not chunk.point_cloud,
		lambda chunk: chunk.buildPoints(**build_point_cloud_config)
	)

build_dense_cloud_job = WorkflowJob(
		"Build dense cloud", 
		lambda chunk: not chunk.dense_cloud,
		lambda chunk: chunk.buildDenseCloud(**build_dense_cloud_config)
	)

build_model_job = WorkflowJob(
		"Build model", 
		lambda chunk: not chunk.model,
		lambda chunk: chunk.buildModel(**build_model_config)
	)

build_texture_job = WorkflowJob(
		"Build texture", 
		lambda chunk: not chunk.model.texture(),
		lambda chunk: chunk.buildTexture(**build_texture_config)
	)

export_model_job = WorkflowJob(
		"Export model", 
		lambda chunk: chunk.model and not export_file_exists(chunk.label, export_model_config['format']),
		lambda chunk: export_model( chunk, chunk.label, export_model_config )
	)

export_texture_job = WorkflowJob(
		"Export texture", 
		lambda chunk: chunk.model.texture() and not export_file_exists(chunk.label, export_model_config['texture_format']),
		lambda chunk: export_texture( chunk, chunk.label )
	)

###########################################################################################################

open_log( HomeDirectory )

log( "--- Starting workflow ---" )
log( "Photoscan version " + PhotoScan.Application().version )
log( "Home directory: " + HomeDirectory )
log_time()

project_dirs = find_project_folders(HomeDirectory, PhotosDirectory)
log( "Found {} project directories".format( len(project_dirs) ) )

log( "Making projects" )

jobs = (
		match_photos_job,
		align_cameras_job, 
		build_point_cloud_job,
		build_dense_cloud_job,
		build_model_job,
		build_texture_job,
		export_model_job,
		export_texture_job
	)

[build(pd, PhotosDirectory, jobs) for pd in project_dirs]

log_time()
log( "--- Finished workflow ---")
close_log()


