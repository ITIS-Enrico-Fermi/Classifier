import cv2 as cv
import argparse
import logging
import os
import numpy as np
import time
from typing import Tuple, List
from enum import Enum, auto
from math import floor, ceil
from cvlib import *

class Dispatcher:
    """
    Collection of tools and utilities class for classification
    """
    def __init__(self, models: List[str], video_source: str = None, image = None) -> None:
        """
        Constructor of the class Classifier
        :param List[str] models: relative path to the xml models
        :param str video_source: video source. If video_source is a string, it's supposed to be the relative path to a file, else video_source is converted to an integer and the video stream is treated like a cam
        """
        self.models_cascade: List[cv.CascadeClassifier] = list()
        for model in models:
            model_cascade: cv.CascadeClassifier = cv.CascadeClassifier()
            model_cascade.load(cv.samples.findFile(model))
            self.models_cascade.append(model_cascade)
        self.video_source: str = video_source  # video_source == None if the classifier will be used on an image
        self.image: str = image  # image == None if the classifier will be used on the video source
        self.start_time_int: int = None  # start_time will fill this attribute for the first time
        self.times: np.array = None  # start will fill this attribute
        self.times_index: int = 0  # Index to keep track of times array filling
        # self.main_window_created: bool = False
        self.is_first_frame: bool = True
        self.colors: List[Tuple[int, int, int]] = random_colors(len(models))
        self.display: Display = Display()

    def __start_time(self) -> None:
        """
        Get current time and save it into self.start_time. Used to compute the elapsed time afterwards
        """
        self.start_time_int = time.time()

    def __end_time(self) -> None:
        """
        Compute elapsed time (between start time and current time) and save it into self.times, in order to figure out what's the average time needed to classify one frame
        """
        logging.info(f"time for 1 frame classification {time.time() - self.start_time_int}")
        if not str.isnumeric(self.video_source):  # If the video source is not a cam
            self.times[self.times_index] = time.time() - self.start_time_int
            self.times_index += 1
    
    def preprocess(self, frame: np.ndarray):
        """
        Shared method for frame preprocessing. Frames are preprocessed only once, and then tested against several models, in order to decrease CPU laod and increase recognition speed
        :param np.ndarray frame: input frame
        :return: processed frame
        """
        frame_gray: np.ndarray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        if self.is_first_frame:
            self.display.set_orientation(frame)
            self.is_first_frame = False
        downscaled_frame_gray: np.ndarray = cv.resize(frame_gray, dsize = self.display.size, interpolation = cv.INTER_AREA)
        downscaled_frame_gray_equalized: np.ndarray = cv.equalizeHist(downscaled_frame_gray)
        return downscaled_frame_gray_equalized

    def detect(self, frame: np.ndarray, processed_frame_preview: bool = False) -> List[Region]:
        """
        Detect objects according to the model
        :param np.ndarray frame: frame against which run the classifier
        :param bool processed_frame_preview: am I supposed to show the processed frame?
        :return: a list of regions where the object has been found
        """
        original_frame = frame
        original_frame_regions_list: List[Region] = list()
        processed_frame_regions_list: List[Region] = list()
        shape: Shape = Shape.RECTANGLE  # Default shape
        self.__start_time()
        for model_cascade, color in zip(self.models_cascade, self.colors):
            if len(set(model_cascade.getOriginalWindowSize())) == 1:
                shape = Shape.ELLIPSE  # Face
            else:
                shape = Shape.RECTANGLE
            processed_frame = self.preprocess(frame)
            obj_list = model_cascade.detectMultiScale(processed_frame, scaleFactor = 1.2)
            scale_factor_x: float = frame.shape[1] / self.display.size[0]  # both shape[1] and size[0] refer to the x (width)
            scale_factor_y: float = frame.shape[0] / self.display.size[1]  # both shape[0] and size[1] refer to the y (height)
            for (x, y, w, h) in obj_list:
                processed_frame_regions_list.append(Region(x, y, w, h, color, shape))
                original_frame_regions_list.append(Region(x*scale_factor_x, y*scale_factor_y, w*scale_factor_x, h*scale_factor_y, color, shape))
        self.__end_time()
        # if processed_frame_preview:
        #     self.display(processed_frame, processed_frame_regions_list, 'Processed frame preview')
        if not processed_frame_preview:
            return original_frame_regions_list, None, None
        else:
            return original_frame_regions_list, processed_frame, processed_frame_regions_list

    def detect_and_display(self, frame: np.ndarray, processed_frame_preview: bool) -> None:
        """
        Detect objects inside the frame, draw a ellipse around them and show the new frame
        :param np.ndarray frame: original frame
        :param bool processed_frame_preview: am I supposed to show the processed frame?
        """
        regions, frame_p, frame_reg_p = self.detect(frame, processed_frame_preview)
        self.display.show(frame, regions, 'Face detection with HCC', 0.4, frame_processed = frame_p, regions_processed = frame_reg_p)

    def start(self, processed_frame_preview: bool) -> None:  # Blocking method
        """
        Start video capture and frames classification. Be aware that it's a blocking method (it enters a loop)
        :param bool processed_frame_preview: am I supposed to show the processed frame?
        """
        if self.image:
            img: np.ndarray = cv.imread(self.image)
            self.detect_and_display(img, processed_frame_preview)
            if cv.waitKey(0) == 27:  # Key ==> 'ESC'
                return

        cap = cv.VideoCapture(int(self.video_source) if str.isnumeric(self.video_source) else self.video_source)
        frames_number: int = int(cap.get(cv.CAP_PROP_FRAME_COUNT))
        if frames_number > 0:  # frames_num < 0 when the video source is a camera
            self.times = np.empty(frames_number, dtype='f', order='C')
        if not cap.isOpened():
            logging.error("Camera video stream can't be opened")
            exit(1)
        while True:
            ret, frame = cap.read()
            if frame is None:
                break
            self.detect_and_display(frame, processed_frame_preview)
            if cv.waitKey(1) == 27:  # Key ==> 'ESC'
                break
        # When classification is done, print the average time needed to classify each frame
        if frames_number > 0:
            logging.info(f"Average time needed to classify each frame {np.average(self.times[:self.times_index])}")
            logging.info(f"Max time needed to classify each frame {np.amax(self.times[:self.times_index])}")
            logging.info(f"Min time needed to classify each frame {np.amin(self.times[:self.times_index])}")

def main(video_source: str, image: str, models_name: str, processed_frame_preview: bool) -> None:
    models = list()
    for model_name in models_name:
        models.append(os.path.join(os.path.split(os.path.abspath(cv.__file__))[0], 'data', model_name))
        
    disp = Dispatcher(models, video_source = video_source, image = image)
    disp.start(processed_frame_preview)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s: %(message)s", datefmt="%H:%M:%S")
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', help='List of cascade classifier model names. Path relative to cv2 install dir', default=['haarcascade_frontalface_default.xml'], nargs='+')
    parser.add_argument('--source', help='Camera number or video filename', type=str, default='0')
    parser.add_argument('--image', help='Image filename', type=str)
    parser.add_argument('--processed-frame-preview', help='Show the preview of processed frame', default=False, action='store_true')
    args = parser.parse_args()
    main(args.source, args.image, args.models, args.processed_frame_preview)