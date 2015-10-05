
import PhotoScan
import datetime
import glob
import os

'''
A workflow to process multiple set of photos in Photoscan.

See the bottom of the file for configuration options and documentation.
'''


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

def log_chunk_data(chunk):
	log("Number of cameras: {}".format(len(chunk.cameras)))
	log("Cameras are aligned: {}".format(are_cameras_aligned(chunk)))
	log("Has sparse cloud: {}".format(chunk.point_cloud is not None))
	log("Has dense cloud: {}".format(chunk.dense_cloud is not None))
	log("Has model: {}".format(chunk.model is not None))


#################################################
# Utility functions

def does_project_exist(project_dir):
	'Does the PhotoScan project file exist'
	project_name = make_project_filename(project_dir, "psz")
	return glob.glob(project_dir + "\\*.psz") is not None	

def are_cameras_aligned(chunk):
	return len([c for c in chunk.cameras if c.center is not None]) == len(chunk.cameras)

def is_valid_project_dir( project_dir, photos_dir ):
	"A valid project directory has a photos subdirectory."
	return photos_dir in os.listdir(project_dir)

def estimate_image_quality(photo):
	return Photoscan.Utils.estimateImageQuality(photo)

def make_project_filename(project_dir, ext):
	'Make a filename in the project directory with the given extension'
	dir_name = os.path.basename(project_dir)
	return os.path.join(project_dir,dir_name + "." + ext);


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
	project_name = make_project_filename(project_dir, "psz")

	doc = PhotoScan.Document()
	if not doc.open( project_name ):
		log( "ERROR: Cold not open document: " + project_name)

	return doc


def make_project(project_dir, photos_dir):
	'Make a new project and add the photos from the photos_dir to it.'

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


def make_or_open_projects(project_dirs, photos_dir):
	return [make_or_open_project(pd, photos_dir) for pd in project_dirs]


def build_chunk(chunk, doc):
	log( "Building chunk" )
	log_time()

	if not chunk.enabled:
		log( "Chunk not enabled, skipping" )

	if not are_cameras_aligned(chunk):
		chunk.matchPhotos(accuracy=PhotoScan.HighAccuracy, preselection=PhotoScan.GenericPreselection)
		if not chunk.alignCameras():
			log( "ERROR: Could not align cameras" )
			return False
		else:
			doc.save()
	else:
		log( "Cameras are already aligned.")


	if not chunk.point_cloud:
		if not chunk.buildPoints():
			log( "ERROR: Could not build sparse cloud" )
			return False
		else:
			doc.save()

	if not chunk.dense_cloud:
		if not chunk.buildDenseCloud(quality=PhotoScan.HighQuality):
			log( "ERROR: Could not build dense cloud" )
			return False
		else:
			doc.save()
	else:
		log( "Dense cloud already exists." )


	if not chunk.model:
		if not chunk.buildModel(surface=PhotoScan.Arbitrary, interpolation=PhotoScan.EnabledInterpolation):
			log( "ERROR: Could not build model")
			return False
		else:
			doc.save()
	else:
		log( "Model already exists" )

	if not chunk.model and not chunk.model.texture:
		if not chunk.buildTexture():
			log( "ERROR: Could not build texture")
			return False
		else:
			doc.save()
	else:
		log( "Texture already exists" )

	log( "Finished building chunk" )

	return True


def build(doc):
	log( "Building " + doc.path )
	log_time()
	if not build_chunk( doc.chunk, doc ):
		return False
	doc.save()
	log( "Finished building" )
	return True


def export(chunk, project_directory):
	log( "Exporting chunk" )

	model_name = make_project_filename(project_directory, "fbx")

	if not os.path.isfile( model_name ):
		if not chunk.exportModel(model_name, binary=True, texture_format="jpg", texture=True, normals=True, colors=True, cameras=False, format="fbx"):
			log( "ERROR: Could not export model " + model_name)
	else:
		log( "Model exists, skipping" )


def build_and_export(project_dir, photos_dir):
	doc = make_or_open_project(project_dir, photos_dir)
	if build(doc):
		dump(doc)
		export( doc.chunk, project_dir )
	else:
		log( "ERROR: Build failed." )


###########################################################################################################

'''
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

The workflow produces an fbx and texture for each directory, which will be placed in the root
of the directory.

This script can be run multiple times to continue processing after a crashed or cancelled processing run. It
will skip stages that have already been completed.
'''

HomeDirectory = "E:\\Captures"
PhotosDirectory = "photos"

open_log( HomeDirectory )

log( "--- Starting workflow ---" )
log( "Photoscan version " + PhotoScan.Application().version )
log( "Home directory: " + HomeDirectory )
log_time()

project_dirs = find_project_folders(HomeDirectory, PhotosDirectory)
log( "Found {} project directories".format( len(project_dirs) ) )

log( "Making projects" )
[build_and_export(pd, PhotosDirectory) for pd in project_dirs]

log_time()
log( "--- Finished workflow ---")
close_log()
