from datetime import datetime
# from pgmagick import Image
import os
import sys
import requests
import urllib
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup



manifest_file = "Master_Manifest.txt"

#This function creates a manifest containing the web urls of every jp2 newspaper page images from Chronicling America.
#It does this by first navigating to the html page that links to each of the batch folders, then scrubs
#through the html source code to acquire the names of each batch folder. Once batch folder names are acquired, the function navigates
#to each batch folder and loads up the manifest for that batch, retrieves the urls for the images from the manifest
#and appends the URLs to the full manifest file.
def buildFullManifest():
    # remove existing manifest file in order to prevent appending to it
    if os.path.exists(manifest_file):
        print("Deleted " + manifest_file + " and generating new one")
        os.remove(manifest_file)
    print("Getting batch urls")
    batchesURL = "http://chroniclingamerica.loc.gov/data/batches/"

    # Ben's code for reading webpage
    # urllib requests were not being processed ("urllib.error.HTTPError: HTTP Error 403: Forbidden")
    # so switched to using BeautifulSoup
    # https://stackoverflow.com/questions/1080411/retrieve-links-from-web-page-using-python-and-beautifulsoup
    headers = {'User-Agent':'Mozilla/5.0'}
    page = requests.get(batchesURL)
    soup = BeautifulSoup(page.text, "html.parser")

    # list of URLs of newspaper info
    listOfBatchURLS = []
    print("finding names")

    # iterate through all of the hrefs to find the links
    for link in soup.find_all('a', href=True):
        # skip over two paths (return to parent directory and other random file)
        if link['href'] == '../' or link['href'] == '.keep':
            continue
        listOfBatchURLS.append(link['href'])

    # prints the total number of links
    print("Number of links found: " +str(len(listOfBatchURLS)))

    length = len(listOfBatchURLS)
    count = 0
    print("starting processing")
    openf = open(manifest_file, "a")
    log = open("build_manifest_log.txt", "a")

    # iterate through scraped URLs
    for j in listOfBatchURLS[:1]:
        count += 1
        sys.stdout.write("\rProcessing "+str(count)+"/"+str(length)+" batch manifests (current: "+j+")")
        sys.stdout.flush()

        # header for request
        headers = {'User-Agent':'Mozilla/5.0'}

        # we open each manifest-md5.txt file to extract the filepaths of the .jp2 images (each image is a scan of a page)
        try:
            # sets path for "manifest-md5.txt"
            path = batchesURL+j+"manifest-md5.txt"
            # load in the full URL (basepath + j)
            page = requests.get(path)
            soup = BeautifulSoup(page.text, "html.parser")

            # creates list for storing image paths
            fullDataPaths = []

            # split lines in .txt
            lines = str(soup).splitlines()

            # then parse each line (we want to grab each image filepath that is in .jp2 format)
            for line in lines:
                partialDataPath = line.split()
                if partialDataPath[1].endswith('.jp2') and partialDataPath[1].count('/') == 4:
                    fullDataPaths.append(batchesURL+j+partialDataPath[1]+'\n')
                    fullDataPaths.sort()

            openf.writelines(fullDataPaths)

        except Exception as e:
            print("Encountered an error with batch " + j + " : "+ str(e) + "\n")
            log.write("Batch " + j + " failed: " + str(e) + "\n")

    openf.close()
    log.close()



#This function, when given a begin year and an end year, will search through the full Manifest file
#and download all images within a year range. For images from a single year, the same year is used for both parameters.
#The images are downloaded to the following directory structure: data/FullPages/BatchLevel/IssueLevel/PageLevel
#This function also uses wget in order to download images, this is due to complications we ran into
#using urllib with the Library of Congress's server.
def getImages(startYear = 1836, endYear = datetime.now().year):
    Error404 = []
    imageCount = 0
    with open(manifest_file, "r") as masterManifest:
        for line in masterManifest:
            lineList = line.split('/')
            imageYear = int(lineList[9][:4])
            if imageYear >= int(startYear) and imageYear <= int(endYear):
                imageCount += 1

    with open(manifest_file, "r") as masterManifest:
        previousLine = ""
        pageCount = 1
        fullCount = 0
        for line in masterManifest:
            lineList = line.split('/')

            #used in construction of the image's filename.
            #ensures consistent naming since each issue of a newspaper shares the same base name
            if lineList[9] == previousLine:
                pageCount += 1
            else:
                pageCount = 1

            imageYear = int(lineList[9][:4])
            if imageYear >= int(startYear) and imageYear <= int(endYear):
                fullCount += 1
                imageURL = line.strip()

                #constructs file and directory names for sorting purposes
                batchName = lineList[5][6:]
                snNumber = lineList[7]
                date = lineList[9][:4]+"-"+lineList[9][4:6]+"-"+lineList[9][6:8]
                edition = lineList[9][-1:]
                issueName = snNumber+"_"+date+"_ed-"+edition
                imageName = issueName+"_seq-"+str(pageCount)+".jp2"

                if not os.path.exists("data/FullPages/"+batchName):
                    os.makedirs("data/FullPages/"+batchName)
                if not os.path.exists("data/FullPages/"+batchName+"/"+issueName):
                    os.makedirs("data/FullPages/"+batchName+"/"+issueName)

                os.chdir("data/FullPages/"+batchName+"/"+issueName)
                print(imageURL)

                try:
                    r = requests.get(imageURL, stream=True)
                    # makes sure the request passed:
                    if r.status_code == 200:
                        with open(imageName, 'wb') as f:
                            f.write(r.content)

                    sys.stdout.write("\rProcessed Image "+str(fullCount)+"/"+str(imageCount)+"           ")
                    sys.stdout.flush()
                    os.chdir("../../../../")

                except:
                    log.write("Download failed: " + str(imageURL) + "\n")

            previousLine = lineList[9]

    print("Files downloaded; check error logs for any failed downloads")


#This function searches through the directory structure created in the getImages function
#and converts all jp2 images to the jpg format. If an image can't be converted, the function adds
#the filename to a list of broken images, and this list is presented at the end of the process.
def convertToJpg():
    problemImages = []
    os.chdir("data/FullPages")
    batchLevel = os.listdir(os.getcwd())
    totalBatches = len(batchLevel)
    currentBatch = 0
    for i in batchLevel:
        currentBatch += 1
        os.chdir(i)
        issueLevel = os.listdir(os.getcwd())
        totalIssues = len(issueLevel)
        currentIssue = 0
        for j in issueLevel:
            currentIssue += 1
            os.chdir(j)
            jp2Images = os.listdir(os.getcwd())
            totalImages = len(jp2Images)
            currentImage = 0
            for k in jp2Images:
                currentImage += 1
                try:
                    if k == '.DS_Store':
                        continue
                    command = "mogrify -resize 60x60% -quality 60 -format jpg " + k
                    os.system(command)

                    #Status update on how many images have been processed
                    sys.stdout.write("\rConverted Batch: "+str(currentBatch)+"/"+str(totalBatches)+" Issue: "+str(currentIssue)+"/"+str(totalIssues)+" Image: "+str(currentImage)+"/"+str(totalImages)+"           ")
                    sys.stdout.flush()
                    #remove old jp2 image to conserve space, also only remove if conversion was successful
                    os.remove(k)
                except:
                    problemImages.append(str(k))
            os.chdir('..')
        os.chdir('..')
    os.chdir('../..')

    #end of process message
    if len(problemImages) > 0:
        print("These are images that could not be converted to jpg for some reason. Please check for corruption/ proper download.")
        print(problemImages)
    else:
        print("All images converted successfully")




def usage():
    print("Usage: python Batch_Retrieval.py [1 | 2 | 3] [YYYY] [YYYY]")
    print("    1 - build manifest and get images")
    print("    2 - get images only")
    print("    3 - build manifest only")
    print("    YYYY - Year beginning and ending (may use same year for both)")
    print("Examples:")
    print("    ./Batch_Retrieval.py 1 1938 1938")
    print("    ./Batch_Retrieval.py 3")

if len(sys.argv) == 1:
    usage()
elif sys.argv[1] == "1":
    print("Preparing to build manifest and get images")
    buildFullManifest()
    getImages(sys.argv[2], sys.argv[3])
    convertToJpg()
elif sys.argv[1] == "2":
    print("Preparing to get images")
    getImages(sys.argv[2], sys.argv[3])
    convertToJpg()
elif sys.argv[1] == "3":
    print("Preparing to build manifest")
    buildFullManifest()
