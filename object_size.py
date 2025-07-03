
from scipy.spatial import distance as dist
from imutils import perspective
from imutils import contours
import numpy as np
import argparse
import imutils
import cv2

def midpoint(ptA, ptB):
    return ((ptA[0] + ptB[0]) * 0.5, (ptA[1] + ptB[1]) * 0.5)

def resize_to_screen(image, max_width=800, max_height=600):
    h, w = image.shape[:2]
    scale_w = max_width / w
    scale_h = max_height / h
    scale = min(scale_w, scale_h, 1)  # never upscale, only downscale

    new_w = int(w * scale)
    new_h = int(h * scale)
    resized = cv2.resize(image, (new_w, new_h))
    return resized

# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--image", required=True,
                help="path to the input image")
ap.add_argument("-w", "--width", type=float, required=True,
                help="width of the left-most object in the image (in inches)")
ap.add_argument("-u", "--unit", type=str, default="inches",
                choices=["inches", "cm", "meters"],
                help="unit of measurement (inches,cm,meters,default: inches)")
args = vars(ap.parse_args())

# unit conversion setup
unit = args["unit"]
if unit == "inches":
    conv_factor = 1
    unit_label = "in"
elif unit == "cm":
    conv_factor = 2.54
    unit_label = "cm"
elif unit == "meters":
    conv_factor = 0.0254
    unit_label = "m"
else:
    conv_factor = 1
    unit_label = "in"

# load the image, convert it to grayscale, and blur it slightly
image = cv2.imread(args["image"])
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
gray = cv2.GaussianBlur(gray, (7, 7), 0)

# perform edge detection, then perform a dilation + erosion to close gaps between edges
edged = cv2.Canny(gray, 50, 100)
edged = cv2.dilate(edged, None, iterations=1) #thickens edges
edged = cv2.erode(edged, None, iterations=1) #thins edges

# find contours in the edge map
cnts = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL,
                        cv2.CHAIN_APPROX_SIMPLE)
cnts = imutils.grab_contours(cnts)

# sort the contours from left-to-right and initialize pixelsPerMetric calibration variable
(cnts, _) = contours.sort_contours(cnts)
pixelsPerMetric = None #not calculated yet

# loop over the contours individually
for c in cnts:
    # ignore small contours that may be noise
    if cv2.contourArea(c) < 100:
        continue

    # compute the rotated bounding box of the contour
    orig = image.copy()
    box = cv2.minAreaRect(c)
    box = cv2.boxPoints(box) if not imutils.is_cv2() else cv2.cv.BoxPoints(box)
    box = np.array(box, dtype="int")

    # order the points and draw the bounding box
    box = perspective.order_points(box)
    cv2.drawContours(orig, [box.astype("int")], -1, (0, 255, 0), 2)

    # draw corner points
    for (x, y) in box:
        cv2.circle(orig, (int(x), int(y)), 5, (0, 0, 255), -1)

    # unpack the ordered bounding box points
    (tl, tr, br, bl) = box
    (tltrX, tltrY) = midpoint(tl, tr)
    (blbrX, blbrY) = midpoint(bl, br)

    (tlblX, tlblY) = midpoint(tl, bl)
    (trbrX, trbrY) = midpoint(tr, br)

    # draw midpoints
    cv2.circle(orig, (int(tltrX), int(tltrY)), 5, (255, 0, 0), -1)
    cv2.circle(orig, (int(blbrX), int(blbrY)), 5, (255, 0, 0), -1)
    cv2.circle(orig, (int(tlblX), int(tlblY)), 5, (255, 0, 0), -1)
    cv2.circle(orig, (int(trbrX), int(trbrY)), 5, (255, 0, 0), -1)

    # draw lines between midpoints
    cv2.line(orig, (int(tltrX), int(tltrY)), (int(blbrX), int(blbrY)),
             (255, 0, 255), 2)
    cv2.line(orig, (int(tlblX), int(tlblY)), (int(trbrX), int(trbrY)),
             (255, 0, 255), 2)

    # compute Euclidean distances between midpoints
    dA = dist.euclidean((tltrX, tltrY), (blbrX, blbrY))
    dB = dist.euclidean((tlblX, tlblY), (trbrX, trbrY))

    # initialize pixelsPerMetric using the known width of left-most object (in inches)
    if pixelsPerMetric is None:
        pixelsPerMetric = dB / args["width"]

    # convert object dimensions to chosen unit
    dimA = (dA / pixelsPerMetric) * conv_factor
    dimB = (dB / pixelsPerMetric) * conv_factor

    # draw the dimensions on the image
    cv2.putText(orig, f"{dimA:.2f} {unit_label}",
                (int(tltrX - 15), int(tltrY - 10)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
    cv2.putText(orig, f"{dimB:.2f} {unit_label}",
                (int(trbrX + 10), int(trbrY)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

    # resize image if too large for screen and display
    resized_image = resize_to_screen(orig)
    cv2.imshow("Image", resized_image)
    cv2.waitKey(0)
