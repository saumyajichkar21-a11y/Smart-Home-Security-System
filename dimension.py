import ezdxf
from ezdxf import units

def create_dxf():
    # Create a new DXF document
    doc = ezdxf.new('R2010')
    doc.units = units.MM
    msp = doc.modelspace()

    # Helper function to draw a rectangle
    def draw_rect(x, y, w, h):
        msp.add_lwpolyline([(x, y), (x+w, y), (x+w, y+h), (x, y+h), (x, y)], close=True)

    # 1. BASE PLATE (300 x 150)
    # Location: 0, 0
    draw_rect(0, 0, 300, 150)

    # 2. BACK WALL (300 x 147)
    # Location: 0, 160
    draw_rect(0, 160, 300, 147)

    # 3. FRONT WALL (300 x 147)
    # Location: 0, 320
    draw_rect(0, 320, 300, 147)
    # -- Door Cutout --
    draw_rect(125, 320, 50, 100) # Centered door
    # -- ESP32-CAM Lens Hole (Above door) --
    msp.add_circle((150, 435), radius=5) 
    
    # -- PIR Sensor Cutout (Left side of front wall) --
    msp.add_circle((60, 380), radius=12) # 24mm diameter for PIR dome

    # 4. LEFT SIDE WALL (144 x 147)
    # Location: 320, 0
    draw_rect(320, 0, 144, 147)

    # 5. RIGHT SIDE WALL - WINDOW (144 x 147)
    # Location: 320, 160
    draw_rect(320, 160, 144, 147)
    # -- Window Cutout --
    draw_rect(362, 210, 60, 50)
    # -- SW-420 Wire hole next to window --
    msp.add_circle((350, 235), radius=2) 

    # 6. INTERNAL PARTITION WALL (144 x 147)
    # Location: 320, 320
    draw_rect(320, 320, 144, 147)
    # -- Buzzer Hole --
    msp.add_circle((392, 420), radius=13) # 26mm diameter for buzzer

    # Save the file
    filename = "Smart_Home_Security_Model.dxf"
    doc.saveas(filename)
    print(f"Success! {filename} has been generated and is ready for laser cutting.")

if __name__ == "__main__":
    create_dxf()