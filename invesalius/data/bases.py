import numpy as np
import invesalius.data.coordinates as dco
import invesalius.data.transformations as tr
import invesalius.data.coregistration as dcr

def angle_calculation(ap_axis, coil_axis):
    """
    Calculate angle between two given axis (in degrees)

    :param ap_axis: anterior posterior axis represented
    :param coil_axis: tms coil axis
    :return: angle between the two given axes
    """

    ap_axis = np.array([ap_axis[0], ap_axis[1]])
    coil_axis = np.array([float(coil_axis[0]), float(coil_axis[1])])
    angle = np.rad2deg(np.arccos((np.dot(ap_axis, coil_axis))/(
        np.linalg.norm(ap_axis)*np.linalg.norm(coil_axis))))

    return float(angle)


def base_creation_old(fiducials):
    """
    Calculate the origin and matrix for coordinate system transformation.
    q: origin of coordinate system
    g1, g2, g3: orthogonal vectors of coordinate system

    :param fiducials: array of 3 rows (p1, p2, p3) and 3 columns (x, y, z) with fiducials coordinates
    :return: matrix and origin for base transformation
    """

    p1 = fiducials[0, :]
    p2 = fiducials[1, :]
    p3 = fiducials[2, :]

    sub1 = p2 - p1
    sub2 = p3 - p1
    lamb = (sub1[0]*sub2[0]+sub1[1]*sub2[1]+sub1[2]*sub2[2])/np.dot(sub1, sub1)

    q = p1 + lamb*sub1
    g1 = p1 - q
    g2 = p3 - q

    if not g1.any():
        g1 = p2 - q

    g3 = np.cross(g2, g1)

    g1 = g1/np.sqrt(np.dot(g1, g1))
    g2 = g2/np.sqrt(np.dot(g2, g2))
    g3 = g3/np.sqrt(np.dot(g3, g3))

    m = np.matrix([[g1[0], g1[1], g1[2]],
                   [g2[0], g2[1], g2[2]],
                   [g3[0], g3[1], g3[2]]])

    m_inv = m.I

    return m, q, m_inv


def base_creation(fiducials):
    """
    Calculate the origin and matrix for coordinate system
    transformation.
    q: origin of coordinate system
    g1, g2, g3: orthogonal vectors of coordinate system

    :param fiducials: array of 3 rows (p1, p2, p3) and 3 columns (x, y, z) with fiducials coordinates
    :return: matrix and origin for base transformation
    """

    p1 = fiducials[0, :]
    p2 = fiducials[1, :]
    p3 = fiducials[2, :]

    sub1 = p2 - p1
    sub2 = p3 - p1
    lamb = np.dot(sub1, sub2)/np.dot(sub1, sub1)

    q = p1 + lamb*sub1
    g1 = p3 - q
    g2 = p1 - q

    if not g1.any():
        g1 = p2 - q

    g3 = np.cross(g1, g2)

    g1 = g1/np.sqrt(np.dot(g1, g1))
    g2 = g2/np.sqrt(np.dot(g2, g2))
    g3 = g3/np.sqrt(np.dot(g3, g3))

    m = np.zeros([3, 3])
    m[:, 0] = g1/np.sqrt(np.dot(g1, g1))
    m[:, 1] = g2/np.sqrt(np.dot(g2, g2))
    m[:, 2] = g3/np.sqrt(np.dot(g3, g3))

    return m, q


def calculate_fre(fiducials_raw, fiducials, ref_mode_id, m_change, m_icp=None):
    """
    Calculate the Fiducial Registration Error for neuronavigation.

    :param fiducials_raw: array of 6 rows (tracker probe and reference) and 3 columns (x, y, z) with coordinates
    :type fiducials_raw: numpy.ndarray
    :param fiducials: array of 6 rows (image and tracker fiducials) and 3 columns (x, y, z) with coordinates
    :type fiducials: numpy.ndarray
    :param ref_mode_id: Reference mode ID
    :type ref_mode_id: int
    :param m_change: 3x3 array representing change of basis from head in tracking system to vtk head system
    :type  m_change:  numpy.ndarray
    :param m_icp: list with icp flag and 3x3 affine array
    :type  m_icp: list[int, numpy.ndarray]
    :return: float number of fiducial registration error
    """
    if m_icp is not None:
        icp = [True, m_icp]
    else:
        icp = [False, None]

    dist = np.zeros([3, 1])
    for i in range(0, 6, 2):
        p_m, _ = dcr.corregistrate_dynamic((m_change, 0), fiducials_raw[i:i+2], ref_mode_id, icp)
        dist[int(i/2)] = np.sqrt(np.sum(np.power((p_m[:3] - fiducials[int(i/2), :]), 2)))

    return float(np.sqrt(np.sum(dist ** 2) / 3))


# The function flip_x_m is deprecated and was replaced by a simple minus multiplication of the Y coordinate as follows:
# coord_flip = list(coord)
# coord_flip[1] = -coord_flip[1]

# def flip_x_m(point):
#     """
#     Rotate coordinates of a vector by pi around X axis in static reference frame.
#
#     InVesalius also require to multiply the z coordinate by (-1). Possibly
#     because the origin of coordinate system of imagedata is
#     located in superior left corner and the origin of VTK scene coordinate
#     system (polygonal surface) is in the interior left corner. Second
#     possibility is the order of slice stacking
#
#     :param point: list of coordinates x, y and z
#     :return: rotated coordinates
#     """
#
#     point_4 = np.hstack((point, 1.)).reshape(4, 1)
#     point_4[2, 0] = -point_4[2, 0]
#
#     m_rot = tr.euler_matrix(np.pi, 0, 0)
#
#     point_rot = m_rot @ point_4
#
#     return point_rot

def transform_icp(m_img, m_icp):
    coord_img = [m_img[0, -1], -m_img[1, -1], m_img[2, -1], 1]
    m_img[0, -1], m_img[1, -1], m_img[2, -1], _ = m_icp @ coord_img
    m_img[0, -1], m_img[1, -1], m_img[2, -1] = m_img[0, -1], -m_img[1, -1], m_img[2, -1]

    return m_img


def object_registration(fiducials, orients, coord_raw, m_change):
    """

    :param fiducials: 3x3 array of fiducials translations
    :param orients: 3x3 array of fiducials orientations in degrees
    :param coord_raw: nx6 array of coordinates from tracking device where n = 1 is the reference attached to the head
    :param m_change: 3x3 array representing change of basis from head in tracking system to vtk head system
    :return:
    """

    coords_aux = np.hstack((fiducials, orients))
    mask = np.ones(len(coords_aux), dtype=bool)
    mask[[3]] = False
    coords = coords_aux[mask]

    fids_dyn = np.zeros([4, 6])
    fids_img = np.zeros([4, 6])
    fids_raw = np.zeros([3, 3])

    # compute fiducials of object with reference to the fixed probe in source frame
    for ic in range(0, 3):
        fids_raw[ic, :] = dco.dynamic_reference_m2(coords[ic, :], coords[3, :])[:3]

    # compute initial alignment of probe fixed in the object in source frame

    # XXX: Some duplicate processing is done here: the Euler angles are calculated once by
    #      the lines below, and then again in dco.coordinates_to_transformation_matrix.
    #
    a, b, g = np.radians(coords[3, 3:])
    r_s0_raw = tr.euler_matrix(a, b, g, axes='rzyx')

    s0_raw = dco.coordinates_to_transformation_matrix(
        position=coords[3, :3],
        orientation=coords[3, 3:],
        axes='rzyx',
    )

    # compute change of basis for object fiducials in source frame
    base_obj_raw, q_obj_raw = base_creation(fids_raw[:3, :3])
    r_obj_raw = np.identity(4)
    r_obj_raw[:3, :3] = base_obj_raw[:3, :3]
    t_obj_raw = tr.translation_matrix(q_obj_raw)
    m_obj_raw = tr.concatenate_matrices(t_obj_raw, r_obj_raw)

    for ic in range(0, 4):
        if coord_raw.any():
            # compute object fiducials in reference frame
            fids_dyn[ic, :] = dco.dynamic_reference_m2(coords[ic, :], coord_raw[1, :])
        else:
            # compute object fiducials in source frame
            fids_dyn[ic, :] = coords[ic, :]
        fids_dyn[ic, 2] = -fids_dyn[ic, 2]

        # compute object fiducials in vtk head frame
        M_p = dco.coordinates_to_transformation_matrix(
            position=fids_dyn[ic, :3],
            orientation=fids_dyn[ic, 3:],
            axes='rzyx',
        )
        M_img = m_change @ M_p

        angles_img = np.degrees(np.asarray(tr.euler_from_matrix(M_img, 'rzyx')))
        coord_img = list(M_img[:3, -1])
        coord_img[1] = -coord_img[1]

        fids_img[ic, :] = np.hstack((coord_img, angles_img))

    # compute object base change in vtk head frame
    base_obj_img, _ = base_creation(fids_img[:3, :3])
    r_obj_img = np.identity(4)
    r_obj_img[:3, :3] = base_obj_img[:3, :3]

    # compute initial alignment of probe fixed in the object in reference (or static) frame
    s0_dyn = dco.coordinates_to_transformation_matrix(
        position=fids_dyn[3, :3],
        orientation=fids_dyn[3, 3:],
        axes='rzyx',
    )

    return t_obj_raw, s0_raw, r_s0_raw, s0_dyn, m_obj_raw, r_obj_img

def compute_robot_to_head_matrix(raw_target_robot):
    """
    :param head: nx6 array of head coordinates from tracking device in robot space
    :param robot: nx6 array of robot coordinates

    :return: target_robot_matrix: 3x3 array representing change of basis from robot to head in robot system
    """
    head, robot = raw_target_robot
    # compute head target matrix
    m_head_target = dco.coordinates_to_transformation_matrix(
        position=head[:3],
        orientation=head[3:],
        axes='rzyx',
    )

    # compute robot target matrix
    m_robot_target = dco.coordinates_to_transformation_matrix(
        position=robot[:3],
        orientation=robot[3:],
        axes='rzyx',
    )
    robot_to_head_matrix = np.linalg.inv(m_head_target) @ m_robot_target

    return robot_to_head_matrix


class transform_tracker_to_robot(object):
    M_tracker_to_robot = np.array([])
    def transformation_tracker_to_robot(self, tracker_coord):
        if not transform_tracker_to_robot.M_tracker_to_robot.any():
            return None

        M_tracker = dco.coordinates_to_transformation_matrix(
            position=tracker_coord[:3],
            orientation=tracker_coord[3:6],
            axes='rzyx',
        )
        M_tracker_in_robot = transform_tracker_to_robot.M_tracker_to_robot @ M_tracker

        translation, angles_as_deg = dco.transformation_matrix_to_coordinates(M_tracker_in_robot, axes='rzyx')
        tracker_in_robot = list(translation) + list(angles_as_deg)

        return tracker_in_robot
