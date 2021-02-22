""" 
.. module:: base

:synopsis: *Provides the factory class :class:`InstrumentModelFactory` for dishing out instrument-model objects
            based on the input dict/json-string specifications, and also provides the :class:`Instrument` class
            to be used as primary means of instrument initialization.*

"""
from instrupy.util import Entity
import uuid
from collections import namedtuple

from .basic_sensor_model import BasicSensorModel
#from .passive_optical_scanner import PassiveOpticalScanner
#from .synthetic_aperture_radar import SyntheticApertureRadar

class InstrumentModelFactory:
    """ Factory class which allows to register and invoke the appropriate instrument-model instance. 
    
    :class:`BasicSensorModel`, :class:`PassiveOpticalScannerModel` and :class:`SyntheticApertureRadarModel`
    instrument-model classes are registered in the factory. Additional user-defined instrument-model classes
    can be registered as shown below: 

    Usage: 
    
    .. code-block:: python
        
        factory = instrupy.InstrumentModelFactory()
        factory.register_instrument_model('Doppler Radar 2021', DopplerRadar)
        instru1 = factory.get_instrument_model('Doppler Radar 2021')

    :ivar _creators: Dictionary mapping instrument type label to the appropriate instrument class. 
    :vartype _creators: dict

    """

    def __init__(self):
        self._creators = {}
        self.register_instrument_model('Basic Sensor', BasicSensorModel)
        #self.register_instrument('Passive Optical Scanner', PassiveOpticalScannerModel)
        #self.register_instrument('Synthetic Aperture Radar', SyntheticApertureRadarModel)

    def register_instrument_model(self, _type, creator):
        """ Function to register instruments.

        :var _type: Instrument type (label).
        :vartype _type: str

        :var creator: Instrument class.
        :vartype creator: Instrument class.

        """
        self._creators[_type] = creator

    def get_instrument_model(self, specs):
        """ Function to get the appropriate instrument-model instance.

        :var specs: Instrument-model specifications which also contains a valid instrument
                    type in the "@type" dict key. The instrument type is valid if it has been
                    registered with the instrument factory instance.
        :vartype _type: dict
        
        """
        _type = specs.get("@type", None)
        if _type is None:
            raise KeyError('Instrument type key/value pair not found in specifications dictionary.')

        creator = self._creators.get(_type)
        if not creator:
            raise ValueError(_type)
        return creator(specs)

class Instrument(Entity):
    """Main class used to initialize instruments with consideration of multiple operating modes. 
       Each operating mode is stored as a of the type of the respective instrument-model class 
       in a variable length list.       

       :ivar _type: Type of instrument.
       :vartype _type: str

       :ivar name: Name of instrument.
       :vartype name: str

       :ivar mode: List of the objects of types corresponding to the instrument type. Each object stores the corresponding mode specifications.
       :vartype mode: list, :class:`instrupy.basic_sensor_model` (or) :class:`instrupy.passive_optical_scanner_model` (or) :class:`instrupy.synthetic_aperture_radar_model`

       :ivar mode_id: List of identifiers of the instrument modes. Note the order of the ids in the list is synced to the order of the modes in :code:`mode` instance variable list.
       :vartype mode_id: list, str

       :ivar _id: Instrument identifier.
       :vartype _id: str

       Usage: 
    
        .. code-block:: python
            
            x = Instrument.from_dict(specs) 
            mode1_fov = x.get_fov(mode=1) 
            metrics = x.calc_data_metrics(mode=4)
            obsv1 = x.synthesize_observations(2459266.6, [{...},{...},{...},.....,{...}], 4) 

    """

    def __init__(self, _type=None, name=None, mode=None, _id=None):
        """ Initialization.
        """
        self._type = str(_type) if _type is not None else None
        self.name = str(name) if name is not None else None
        self.mode = mode if mode is not None else None

        if(self.mode):     
            # Make list of all mode ids. Note the order of the ids in the list is synced to the order of the modes in self.mode list.
            self.mode_id = []
            for m in self.mode:
                self.mode_id.append(m.get_id())

        super(Instrument,self).__init__(_id, "Instrument")        

    @staticmethod
    def from_dict(d):
        """ Parses an instrument from a normalized JSON dictionary.

        :param d: Normalized JSON dictionary with the corresponding instrument specifications. 
        :paramtype d: dict

        :returns: Instrument object initialized with the input specifications.
        :rtype: :class:`instrupy.Instrument`

        """
        # check and store instrument type
        _type = d.get("@type", None)
        if _type is None:
            raise KeyError('Instrument type key/value pair not found in specifications dictionary.')

        # ensure valid id for the instrument
        if("@id" in d):
            _id = d["@id"]
        else:
            _id = uuid.uuid4() # assign a random id.
            d.update({"@id":_id})

        fac = InstrumentModelFactory()
        if(d.get("mode", None)): # multiple modes may exist
            mode_specs = d["mode"] # a list
            mode = [] # list of instrument objects with the corresponding mode-spec
            for idx, _spec in enumerate(mode_specs): # iterate over list of mode-d
                
                ##### Start create mode specifications dict by combining the data specific to the mode and common data #####

                _mode = {key:val for key, val in d.items() if key != 'mode'} # copy all common d to new dict                 
                # ensure valid mode id
                if(_spec.get("@id", None) is not None): # check if mode id is specified by user
                   _mode_id = str(_spec["@id"])      
                   del _spec['@id']              
                else: 
                   _mode_id = str(idx) # assign a mode-id
                
                _mode.update({"@id":_mode_id})                
                # update and copy the mode specific specifications to the mode dict   
                _mode.update(_spec) 

                ##### End create mode specifications dict #####       
                
                mode.append(fac.get_instrument_model(d))
                
        else:
            # no mode definition => default single mode of operation is to be considered
            mode = [fac.get_instrument_model(d)]
        
        return Instrument( _type = _type,
                           name = d.get('name', None),
                           mode = mode,
                           _id = _id                          
                          )
    
    def to_dict(self):
        """ Translate the Instrument object to a Python dictionary such that it can be uniquely reconstructed back from the dictionary.

        :returns: Instrument specifications as python dictionary.
        :rtype: dict

        """
        d = dict({
                  "@type":  self._type,
                  "name" :  self.name,
                  "@id"  :  self._id
                  })
        mode_dict = []
        for _mode in self.mode:
            mode_dict.append(_mode.to_dict())
        d.update({"mode": mode_dict})
        return d
    
    def __repr__(self):
        return "Instrument.from_dict({})".format(self.to_dict())

    def get_id(self):
        """ Get instrument identifier.

        :returns: Instrument identifier.
        :rtype: str

        """
        return self._id
    
    def get_type(self):
        """ Get instrument type.

        :returns: Instrument type.
        :rtype: str
        
        """
        return self._type

    def get_fov(self, mode_id = None):
        """ Get field-of-view (of a specific instrument mode). If no mode identifier is specified, the 
            the first mode in the list of modes of the instrument is considered.

        :param mode_id: Identifier of the mode.
        :paramtype mode_id: str
        
        :returns: Field-of-view (of a specific instrument mode).
        :rtype: :class:`instrupy.util.ViewGeometry`
        
        """ 
        if mode_id is not None:
            _mode_id_indx = self.mode_id.index(mode_id)
            _mode = self.mode[_mode_id_indx]
        else:
            _mode = self.mode[0]
        
        return _mode.fieldOfView

    def get_orien(self, mode_id = None):
        """ Get orientation (of a specific instrument mode). If no mode identifier is specified, the 
            the first mode in the list of modes of the instrument is considered.

        :param mode_id: Identifier of the mode.
        :paramtype mode_id: str

        :returns: Orientation (of a specific instrument mode).
        :rtype: :class:`instrupy.util.Orientation`
        
        """
        if mode_id is not None:
            _mode_id_indx = self.mode_id.index(mode_id)
            _mode = self.mode[_mode_id_indx]
        else:
            _mode = self.mode[0]
        
        return _mode.orientation
    
    def get_pixel_config(self, mode_id = None):
        """ Get pixel-configuration (of a specific instrument mode). If no mode identifier is specified, the 
            the first mode in the list of modes of the instrument is considered.

        :param mode_id: Identifier of the mode.
        :paramtype mode_id: str
        
        :returns: Pixel-configuration (of a specific instrument mode).
        :rtype: namedtuple, (int, int)
        
        """
        if mode_id is not None:
            _mode_id_indx = self.mode_id.index(mode_id)
            _mode = self.mode[_mode_id_indx]
        else:
            _mode = self.mode[0]

        return _mode.get_pixel_config()

    def calc_data_metrics(self, mode_id=None, *args, **kwargs):
        """ Calculate the observation data metrics associated with the instrument. Please refer to the documentation 
            of the instrument-model of interest for description on the calculations. 

        :param mode_id: Identifier of the mode.
        :paramtype mode_id: str

        :param \*args: Positional arguments. Refer to the ``calc_data_metrics(...)`` function of the instrument model class of interest. 

        :param \**kwargs: Keyword arguments. Refer to the ``calc_data_metrics(...)`` function of the instrument model class of interest. 
            
        """       
        if mode_id is not None:
            _mode_id_indx = self.mode_id.index(mode_id)
            _mode = self.mode[_mode_id_indx]
        else:
            _mode = self.mode[0]
        
        obsv_metrics = _mode.calc_typ_data_metrics(*args, **kwargs)
        return obsv_metrics    
    
    def synthesize_observation(self, mode_id=None, *args, **kwargs):
        """ Compute the value of the geophysical variable (associated with the instrument) at the input pixel (center) positions. 
            
        :param mode_id: Identifier of the mode.
        :paramtype mode_id: str

        :param \*args: Positional arguments. Refer to the ``synthesize_observation(...)`` function of the instrument-model class of interest. 

        :param \**kwargs: Keyword arguments. Refer to the ``synthesize_observation(...)`` function of the instrument-model class of interest. 
            
        """
        if mode_id is not None:
            _mode_id_indx = self.mode_id.index(mode_id)
            _mode = self.mode[_mode_id_indx]
        else:
            _mode = self.mode[0]
        
        return _mode.synthesize_observation(*args, **kwargs)

