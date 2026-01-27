import cv2
import numpy as np
from PIL import ImageFont, ImageDraw, Image
import textwrap
import array



# http://web.archive.org/web/20130115175340/http://nadiana.com/pil-tutorial-basic-advanced-drawing#Drawing_a_Heart
def heart(size, fill):
    width, height = size
    im = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    polygon = [
        (width / 10, height / 3),
        (width / 10, 81 * height / 120),
        (width / 2, height),
        (width - width / 10, 81 * height / 120),
        (width - width / 10, height / 3),
    ]
    draw.polygon(polygon, fill=fill)
    draw.ellipse((0, 0,  width / 2, 3 * height / 4), fill=fill)
    draw.ellipse((width / 2, 0,  width, 3 * height / 4), fill=fill)
    return im

# https://www.perplexity.ai/search/python-pillow-how-do-a-put-an-.fqkXAWMTdWmUaBRYhMeow
# https://www.geeksforgeeks.org/generate-square-or-circular-thumbnail-image-with-python-pillow/
def create_circular_image(input_image_path, size_y):
    # Open the input image
    img = Image.open(input_image_path).convert("RGBA")
    s = size_y / float(img.size[1])
    img = img.resize( (int(s*img.size[0]), int(s*img.size[1])) )
    
    # Create a white background image
    size = img.size
    mask = Image.new('L', size, 0)
    
    # Draw a white circle on the mask
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)
    
    # Apply the mask to the input image
    output = Image.new('RGBA', size, (0, 0, 0, 0))
    output.paste(img, (0, 0), mask)

    return output, mask

# convert an rgba pillow image to an bgra pillow image
def rgba2bgra(img):
        # RGBA to BGRA: https://stackoverflow.com/questions/4661557/pil-rotate-image-colors-bgr-rgb
        img = np.array(img)
        img = img[:,:,[2,1,0,3]] 
        return Image.fromarray(img)


# very basic immediate mode gui 
class Gui:
    def __init__(self, fullscreen: bool = False):
        #img_background = 255*np.ones((768,1024,3),dtype='uint8')
        #img source: https://www.deviantart.com/saiyagina/art/Mystical-Llama-159305987
        #self.img_background = cv2.imread('assets/mystical_llama_by_saiyagina_d2muhab-fullview.jpg')        
        
        self.img_background = cv2.imread('assets/Llama_bg_resized_vertical.jpg')

        w = self.img_background.shape[1]
        h = self.img_background.shape[0]
        cv2.rectangle(self.img_background,(0,h), (w, h-40), (255,255,255),-1)
        self.img = self.img_background.copy()
                
        self.position = 0
        
        # related tp conversation thread rendering
        font_path = ""
        #font_path = "/usr/share/fonts/truetype/liberation/" # linux mint
        font_path = "/Users/amica/Library/Fonts/"
        font_name = font_path + "LiberationSans-Regular.ttf"     
        self.font_size = 24
        self.font = ImageFont.truetype(font_name, self.font_size)
        self.conversation_offset_y = 0
        self.bubble_size = [] # stores the size of the text bubbles
        # https://stackoverflow.com/questions/8257147/wrap-text-in-pil
        self.wrapper = textwrap.TextWrapper(width=60)
        self.img_heart = heart((50, 40), "red")
        
        tmp, _ = create_circular_image('assets/Expanded_Llama_Mona_Lisa_Eyes.png', 100)
        self.img_llama = rgba2bgra(tmp)
        
        self.volumebuffer =  array.array('i')
        
        if fullscreen == True:
            cv2.namedWindow("Amica", cv2.WND_PROP_FULLSCREEN)
            cv2.setWindowProperty("Amica",cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)
            # cv2.setMouseCallback("window", on_mouse, param = 0) # todo: implement scrolling
        else:
            cv2.namedWindow("Amica")

        self._conversation_cache = {
            "conversation": None,
            "offset": None,
            "img": None,
        }


    
    def render_conversation_pil(self, img, conversation):

        # Caching optimisation: only re-render if conversation or offset changes
        conversation_tuple = tuple(conversation)
        oy = self.conversation_offset_y
        cache = self._conversation_cache
        if (
            cache["conversation"] == conversation_tuple and
            cache["offset"] == oy
        ):
            return cache["img"].copy()

        w = self.img_background.shape[1]
        h = self.img_background.shape[0]

        col = (0,0,0) 
        img_pil = Image.fromarray(img).convert("RGBA")
        draw = ImageDraw.Draw(img_pil)

    
        speaker = 0
        cx = 0
        cy = 25  #- int(self.conversation_offset_y)
        i = 0
        for text in conversation:
    
            text_wrapped = self.wrapper.wrap(text)
            text_wrapped = "\n".join(text_wrapped)
                           
            # whatsapp colours for chat bubbles:
            # "#dcf8c6" # whatsapp tea green
            # "#ece5dd" # whatsapp white chocolate
            # if speaker == 0: col = "#ffffff" #"#dde5ec" # whatsapp white chocolate
            if speaker == 0: col = "#dde5ec" # whatsapp white chocolate
            if speaker == 1: col = "#c6f8dc" # whatsapp tea green bgr
            
            if i >= len(self.bubble_size):
                self.bubble_size.append(h) # append a fictional bubble size. will be updated with correct value a few lines later.
                
            # the following instructions are potentially time-consuming.
            # only render and measure text if it is visible.
            if cy+oy + self.bubble_size[i] > 0: #800 for stopping bubbles below the original background image
                # measure wrapped text dimensions
                rect_txt = draw.multiline_textbbox((0,0), text_wrapped, font=self.font)
                # add padding for the bubble rounded rectangle
                p = int(0.75*self.font_size) 
                rect_box = tuple(np.add(rect_txt, (-p, -p, p, p)))
                # calculate bubble position
                bw = rect_box[2] - rect_box[0]
                bh = rect_box[3] - rect_box[1]                
                #cx = int(0.5*w-0.5*bw) + 100*speaker - 50 # variant with bubbles centered and then shifted left / right depending on speaker
                if speaker == 0: cx = 50 # left aligned bubble 
                if speaker == 1: cx = w - 50 - bw # right aligned bubble 

                rect_txt = tuple(np.add(rect_txt, (cx, cy+oy, cx, cy+oy)))
                rect_box = tuple(np.add(rect_box, (cx, cy+oy, cx, cy+oy)))
                # draw bubble and text
                draw.rounded_rectangle(rect_box, radius=15, fill=col, outline="#000000", width=2)
                draw.multiline_text(rect_txt, text_wrapped, font=self.font, fill = "#000000")
                # draw character image to the side of the bubble
                if speaker == 1:
                    img_pil.paste(self.img_llama, (int(cx - self.img_llama.size[0]-p-10), int(cy+oy+0.5*bh-0.5*self.img_llama.size[1])), self.img_llama)
                    if bh < self.img_llama.size[1] - 25:
                        cy += (self.img_llama.size[1] - bh) / 2 # add extra spacing if the bubble is smaller than the llama image
                # update bubble size value
                self.bubble_size[i] = bh 

            # advance cursor position, add spacing between bubbles
            cy += self.bubble_size[i]
            cy += 25
            
            # switch speaker 
            speaker = (speaker+1) % 2 
            i += 1
    
        # scoll up using an offset
        lower_chat_border = h - 100
        #self.conversation_offset_y = lower_chat_border - cy
        new_offset = 0.8 * self.conversation_offset_y + 0.2 * (lower_chat_border - cy)
        if new_offset - (lower_chat_border - cy) < 1:
            self.conversation_offset_y = int(lower_chat_border - cy)
        else:
            self.conversation_offset_y = new_offset
    
        # TODO: render chatbox into main window using alpha channels
        # https://stackoverflow.com/questions/14063070/overlay-a-smaller-image-on-a-larger-image-python-opencv
    
        result_img = np.array(img_pil)
        # Update cache
        self._conversation_cache = {
            "conversation": conversation_tuple,
            "offset": oy,
            "img": result_img.copy(),
        }
        return result_img

      
    
    def draw(self, volume, recording_state, conversation, language='en'):
        # visualize
        w = self.img_background.shape[1]
        h = self.img_background.shape[0]
        self.img = self.img_background.copy()
        
        col = (100,100,100) # light grey color if not recording
        if recording_state == True: 
            col = (0,255,0) # bright green color if recording
        
        self.img = self.render_conversation_pil(self.img, conversation)

        
        # draw the input volume visualization bar
        v = int((self.img.shape[1]-20) * volume / np.iinfo(np.int16).max)
        cv2.rectangle(self.img, (10, h-10), (w-10, h-30), (255,255,255), -1)
        cv2.rectangle(self.img, (10, h-10), (10+v, h-30), col, -1)            
        cv2.rectangle(self.img, (10, h-10), (w-10, h-30), (50,50,50), 2)

        # visualize audio data
        if language == 'en': instruction = 'Press and hold the microphone button to speak!'
        if language == 'de': instruction = 'Druecke und halte die Mikrofontaste, um zu sprechen!'
        p = self.position
        s2 = 80 # size of the microphone symbol
        s22 = int(s2/2)
        
        # volume waveform line length
        v = int(s22 * volume / np.iinfo(np.int16).max)

        # erase the waveform visualization area with a white background
        cv2.rectangle(self.img, (0, h-40), (w, h-40-s2), (255,255,255), -1) 
    
        # draw the recording state circle
        cv2.circle(self.img,    (s22, h-40-s22), s22-4, col, -1)
        
        # if not recording, print "press the microphone button" statement
        if recording_state == False:
            #self.volumebuffer.clear() # only available with python >= 3.13
            self.volumebuffer = array.array('i')
            cv2.putText(self.img, instruction, (s2+10, h-40-s22+12),
                        fontFace = cv2.FONT_HERSHEY_DUPLEX, 
                        #fontFace = cv2.FONT_HERSHEY_TRIPLEX, 
                        fontScale = 1, color=(100,0,0), thickness=1, lineType=cv2.LINE_8)

        # if recording, visualize the waveform and draw recording progress line
        if recording_state == True:
            self.volumebuffer.append(v)
            p = s2
            for v in self.volumebuffer:
                cv2.line(self.img, (p, h-40), (p, h-40-s2), (255,255,255)) # erase
                cv2.line(self.img, (p, h-40-s22+v), (p, h-40-s22-v), (255,0,150)) # draw volume                                
                p = p + 1

            cv2.line(self.img, (p, h-40), (p, h-40-s2), (0,0,0)) # draw progress line indicator
        
        

        cv2.imshow("Amica", self.img)
        
  
    # render conversation thread using only opencv 
    # downside: limited font quality
    def render_conversation_opencv(self, conversation):
        
        w = self.img_background.shape[1]
        h = self.img_background.shape[0]
        
        oy = self.conversation_offset_y
        cx = 0 # cursor coordinates
        cy = 0
        box_w = 600 # width of box to render the text into
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        font_weight = 1
        line = ""
        speaker = 0
        for c in conversation: 
            words = c.split(' ') # words
            for word in words:
                word_size, baseline = cv2.getTextSize(word+' ', font, font_scale, font_weight)
                if cx+word_size[0] < box_w:
                    cx+=word_size[0]
                    line += word + ' '
                else: # render line, reset cursor_x, increase cursor_y
                       
                    x_offset = 100*speaker - 50
                    if speaker == 0: col = (255,200,200)
                    if speaker == 1: col = (200,200,255)
                    cv2.putText(self.img, line, (x_offset + int(0.5*w - 0.5*box_w), 50+cy-oy), fontFace = font, fontScale = font_scale, thickness=font_weight, color=col)
                    cx = 0
                    cy += word_size[1] + baseline + 5
                    line = word + ' '
            
            # print remaining line
            if len(line)>0:
                cv2.putText(self.img, line, (x_offset + int(0.5*w - 0.5*box_w), 50+cy-oy), fontFace = font, fontScale = font_scale, thickness=font_weight, color=col)
                cx = 0
                cy += word_size[1] + baseline + 5
                line = ''
            
            # some spacing between conversations
            cy += 25
            speaker = (speaker+1) % 2 # switch speaker 
            
        # scoll up using an offset
        lower_chat_border = h - 200
        if cy > lower_chat_border:
            self.conversation_offset_y = cy - lower_chat_border            

