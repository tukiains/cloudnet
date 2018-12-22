""" Functions for Categorize output file writing."""
import netCDF4
import uuid
from datetime import datetime, timezone


class CnetVar:
    """Class for Cloudnet variables. Needs refactoring.
    """
    def __init__(self, name, data, data_type='f4', size=('time', 'height'),
                 zlib=True, fill_value=True,
                 long_name=None, units=None,
                 comment=None, plot_scale=None,
                 plot_range=None, extra_attributes=None):
        # Required:
        self.name = name
        self.data = data
        self.data_type = data_type
        self.size = size
        self.zlib = zlib
        if isinstance(fill_value, bool):
            self.fill_value = netCDF4.default_fillvals[data_type]
        else:
            self.fill_value = fill_value
        # Optional:
        self.long_name = long_name
        self.units = units
        self.comment = comment
        self.plot_scale = plot_scale
        self.plot_range = plot_range
        self.extra_attributes = extra_attributes

    def valid_attrs(self):
        """Return (optional) attributes that actually have a value."""
        out = {}
        fields = ('long_name', 'units', 'comment', 'plot_range', 'plot_scale')
        for field in fields:
            value = getattr(self, field)
            if value:
                out[field] = value
        return out


def write_vars2nc(rootgrp, obs):
    """Iterate over Cloudnet instances and write to given rootgrp."""
    for var in obs:
        ncvar = rootgrp.createVariable(var.name, var.data_type, var.size,
                                       zlib=var.zlib, fill_value=var.fill_value)
        ncvar[:] = var.data
        for attr in var.valid_attrs():
            setattr(ncvar, attr, getattr(var, attr))
        if var.extra_attributes:
            for attr, value in var.extra_attributes.items():
                setattr(ncvar, attr, value)


def _copy_dimensions(file_from, file_to, dims_to_be_copied):
    """Copies dimensions from one file to another. """
    for dname, dim in file_from.dimensions.items():
        if dname in dims_to_be_copied:
            file_to.createDimension(dname, len(dim))


def _copy_variables(file_from, file_to, vars_to_be_copied):
    """Copies variables (and their attributes) from one file to another."""
    for vname, varin in file_from.variables.items():
        if vname in vars_to_be_copied:
            varout = file_to.createVariable(vname, varin.datatype, varin.dimensions)
            varout.setncatts({k: varin.getncattr(k) for k in varin.ncattrs()})
            varout[:] = varin[:]


def _copy_global(file_from, file_to, attrs_to_be_copied):
    """Copies global attributes from one file to another."""
    for aname in file_from.ncattrs():
        if aname in attrs_to_be_copied:
            setattr(file_to, aname, file_from.getncattr(aname))


def save_cat(file_name, time, height, model_time, model_height,
             obs, dvec, aux):
    rootgrp = netCDF4.Dataset(file_name, 'w', format='NETCDF4_CLASSIC')
    # create dimensions
    time = rootgrp.createDimension('time', len(time))
    height = rootgrp.createDimension('height', len(height))
    model_time = rootgrp.createDimension('model_time', len(model_time))
    model_height = rootgrp.createDimension('model_height', len(model_height))
    # root group variables
    write_vars2nc(rootgrp, obs)
    # global attributes:
    rootgrp.Conventions = 'CF-1.7'
    rootgrp.title = 'Categorize file from ' + aux[0]
    rootgrp.institution = 'Data processed at the ' + aux[1]
    rootgrp.year = int(dvec[:4])
    rootgrp.month = int(dvec[5:7])
    rootgrp.day = int(dvec[8:])
    #rootgrp.software_version = version
    #rootgrp.git_version = ncf.git_version()
    rootgrp.file_uuid = str(uuid.uuid4().hex)
    rootgrp.references = 'https://doi.org/10.1175/BAMS-88-6-883'
    rootgrp.history = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S") + ' - categorize file created'
    rootgrp.close()


def status_name(long_name):
    """ Default retrieval status variable name """
    return long_name + ' retrieval status'


def bias_name(long_name):
    """ Default bias variable name """
    return 'Possible bias in ' + long_name.lower() + ', one standard deviation'


def err_name(long_name):
    """ Default error variable name """
    return 'Random error in ' + long_name.lower() + ', one standard deviation'


def err_comm(long_name):
    """ Default error comment """
    return ('This variable is an estimate of the one-standard-deviation random error in ' + long_name.lower() + '\n',
            'due to the uncertainty of the retrieval, including the random error in the radar and lidar parameters.')


def bias_comm(long_name):
    """ Default bias comment """
    return ('This variable is an estimate of the possible systematic error (one-standard-deviation) in ' + long_name.lower() + '\n',
            'due to the uncertainty in the calibration of the radar and lidar.')
