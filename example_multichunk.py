
import PhotoScan
import datetime
import glob
import os


#################################################
# Helper functions

def log(msg):
	print(msg)


def log_time():
	log( datetime.datetime.now() )


def make_project_filename(project_dir, ext):
	'Make a filename in the project directory with the given extension'
	dir_name = os.path.basename(project_dir)
	return os.path.join(project_dir,dir_name + "." + ext);


def get_subdirectories(parent_dir):
	'Find all the folders in the parent_dir'
	subdirs = os.listdir(parent_dir) # Get the files and directories
	subdirs = [os.path.join(parent_dir,sd) for sd in subdirs] # Make them into a full path
	subdirs = [sd for sd in subdirs if os.path.isdir(sd)] # Filter to just aget directories
	return subdirs


def make_project(project_dir, chunk_dirs):
	'Make a new project and a chunk for each directory.'

	log( "Making project " + project_dir )

	# Create new doc
	doc = PhotoScan.Document() # Operate on a new document for batch proecssing
	#doc = PhotoScan.app.document # Use the current open document in PhotoScan

	# Go through each chunk directory
	for chunk_dir in chunk_dirs:
		chunk = doc.addChunk() # Create the chunk
		chunk.label = os.path.basename(chunk_dir)
		photos = os.listdir(chunk_dir) # Get the photos filenames
		photos = [os.path.join(chunk_dir,p) for p in photos] # Make them into a full path
		log( "Found {} photos in {}".format(len(photos), chunk_dir))
		if not chunk.addPhotos(photos):
			log( "ERROR: Failed to add photos: " + str(photos))

	# Save the new project
	project_name = make_project_filename(project_dir, "psz")
	log( "Saving: " + project_name );
	if not doc.save( project_name ):
		log( "ERROR: Failed to save project: " + project_name)

	return doc


#################################################
# Configuration

''' 
Expects a folder structure something like:
<HomeDirectory>
	ChunkDirectory1
		photo1.tif
		photo2.tif
	ChunkDirectory2
		photo1.tif
		photo2.tif		

Creates a Photoscan document with a chunk for each ChunkDirectory.
'''


# The directory that has the chunk subfolders.
HomeDirectory = "E:\\Captures\\TestChunks"

# The parameters used to match the photos
match_photos_config = {
	'accuracy': PhotoScan.HighAccuracy,
	'preselection': PhotoScan.GenericPreselection,
}

# The parameters used to build the dense point cloud
build_dense_cloud_config = {
	'quality': PhotoScan.HighQuality
}

# The parameters used to build the model
build_model_config = {
	'surface': PhotoScan.Arbitrary, 
	'interpolation': PhotoScan.EnabledInterpolation
}


#################################################
# Processing
# This is the where the work happens!

log( "--- Starting workflow ---" )
log( "Photoscan version " + PhotoScan.Application().version )
log( "Home directory: " + HomeDirectory )
log_time()

chunk_dirs = get_subdirectories(HomeDirectory)
log( "Found {} project directories".format( len(chunk_dirs) ) )

doc = make_project(HomeDirectory, chunk_dirs)

for chunk in doc.chunks:
	log( "Processing chunk" )

	# Here's where you process the chunk

	# Some examples of what you can do, uncomment as needed.

	#chunk.matchPhotos(**match_photos_config)
	#chunk.alignCameras()
	#chunk.buildPoints()
	#chunk.buildDenseCloud(**build_dense_cloud_config)
	#chunk.buildModel(**build_model_config)
	#chunk.buildTexture(**build_texture_config)



log_time()
log( "--- Finished workflow ---")

