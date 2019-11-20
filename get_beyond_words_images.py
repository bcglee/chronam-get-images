import json
import sys
import urllib
import requests
from PIL import Image, ImageDraw
import time
import math
import os

# resampling scale
scale = 4

# this function downscales according to scale defined above
def rescale(dimension):
    return math.floor(dimension/float(scale))


# first we open the beyond words data (cached in beyond_words_data for reproducability, but can be found here:  http://beyondwords.labs.loc.gov/data)
with open('beyond_words_data/beyond_words.txt') as f:
    bw = json.load(f)

# grabs the data containing the list of annotated images
contents = bw["data"]

# quick print of stats
print("Total # of annotations: " + str(len(contents)))

# create log for storing pages that don't download
log = open("build_manifest_log.txt", "a")

# find the number of unique images
paths = []
for annotation in contents:
    paths.append(annotation["location"]["standard"])

unique_paths = list(set(paths))
print("Number of unique images: "+ str(len(unique_paths)))

# constructing dictionary for accessing the width and height of each image
image_dim_dict = {}
for path in unique_paths:
    for annotation in contents:
        if path in image_dim_dict:
            continue
        if path == annotation["location"]["standard"]:
            image_dim_dict[path] = {"width": annotation["width"], "height": annotation["height"]}

# sets count for observing progress in outer loop
ct = 1

# now, we iterate through each unique path and grab the image using requests
# we also find all corresponding annotations and draw masks
for path in unique_paths:  #can truncate (e.g., [:10]) for testing here

    # destination filepath of image
    destination = "beyond_words_data/extracted/" + path.replace('/', '_')

    # if the file already exists in the directory, we skip
    # this is simply to handle the case in which the code times out, etc.
    if os.path.exists(destination):
        print("Already processed...")
        continue

    # here, we try to pull down the image (if the request isn't stale)
    try:
        r = requests.get(path, stream=True)
        # makes sure the request passed:
        if r.status_code == 200:
            with open(destination, 'wb') as f:
                f.write(r.content)

            # resize image for ease of use
            time.sleep(0.1)
            im = Image.open(destination)
            im = im.resize( (rescale(im.size[0]),rescale(im.size[1])), Image.ANTIALIAS)
            im.save(destination)

        sys.stdout.write("\rProcessed Image "+str(ct)+"/"+str(len(unique_paths))+"           ")
        sys.stdout.flush()

    except:
        log.write("Download failed: " + str(path) + "\n")

    # im = Image.open(destination)
    # im_width, im_height = im.size

    im_width = rescale(image_dim_dict[path]["width"])
    im_height = rescale(image_dim_dict[path]["height"])

    # now, we construct the label image to add the annotations
    label = Image.new(mode = "RGB", size = (im_width, im_height))
    draw  = ImageDraw.Draw(label)
    draw.rectangle(((0, 0), (im_width, im_height)), fill="black")

    # counts the number of annotations per image
    n_annotations = 0

    # list storing booleans of whether the annotation has been processed already
    processed_list = [False]*len(contents)

    # we now find all of the annotations corresponding to this image
    for i in range(0, len(contents)):

        # if this annotation has already been processed for another inmage, we skip it and move on
        if processed_list[i] == True:
            continue

        # pulls off the annotation
        annotation = contents[i]

        # pulls off filepath for annotation
        location = annotation["location"]["standard"]

        # if the annotation corresponds to ths image, we record the annotation on the label image
        if location == path:

            # pull off the other values we need
            id = annotation["id"]
            annotation_region = annotation["region"]
            im_width = annotation["width"]
            im_height = annotation["height"]

            category = ''

            # pulling off annotation category requires conditional parsing based on structure of dictionary
            # (some annotations have "values" defined, and the annotation data lives inside as a the 0th element)
            if 'category' in annotation["data"]:
                category = annotation["data"]["category"]
            elif 'values' in annotation["data"]:
                if 'category' in annotation["data"]["values"][0]:
                    category = annotation["data"]["values"][0]["category"]
                else:
                    log.write("Annotation failed: " + str(annotation) + "\n")


            # if the category wasn't found for whatever reason, we skip
            if category == '':
                continue

            # sets coordinates of annotation region
            x1 = rescale(annotation_region["x"])
            x2 = rescale(annotation_region["x"] + annotation_region["width"])
            y1 = rescale(annotation_region["y"])
            y2 = rescale(annotation_region["y"] + annotation_region["height"])

            # add annotation to label image based on category type
            if category == 'Photograph':
                draw.rectangle(((x1, y1), (x2, y2)), fill="red")
            elif category == 'Map':
                draw.rectangle(((x1, y1), (x2, y2)), fill="green")
            elif category == 'Comics/Cartoon':
                draw.rectangle(((x1, y1), (x2, y2)), fill="blue")

            # increment the number of annotations per the specific image
            n_annotations += 1

            # flag that this annotation has been processed already and doesn't need to be re-processed
            processed_list[i] = True

    print("Number of annotations for this image: " + str(n_annotations))

    # constructs filepath for downloaded image
    label_path = "beyond_words_data/labels/" + path.replace('/', '_')

    # save the constructed image
    label.save(label_path, "PNG")

    # increment count for log
    ct += 1

    # sys.exit()
