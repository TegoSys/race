/**
 * GPS Projection Utilities
 * Implements Equirectangular projection to map GPS coordinates to X,Y coordinates in meters.
 */

export const EARTH_RADIUS = 6371000; // Earth's radius in meters

/**
 * Converts degrees to radians.
 */
export const toRadians = (deg: number): number => (deg * Math.PI) / 180;

/**
 * Maps GPS coordinates to X,Y coordinates in meters relative to a reference origin.
 *
 * @param lat Current latitude in degrees
 * @param lon Current longitude in degrees
 * @param refLat Reference latitude (origin) in degrees
 * @param refLon Reference longitude (origin) in degrees
 * @returns Coordinates in meters { x, y }
 */
export const projectGPS = (
  lat: number,
  lon: number,
  refLat: number,
  refLon: number
): { x: number; y: number } => {
  const latRad = toRadians(lat);
  const lonRad = toRadians(lon);
  const refLatRad = toRadians(refLat);
  const refLonRad = toRadians(refLon);

  // X = R * deltaLon * cos(refLat)
  const x = EARTH_RADIUS * (lonRad - refLonRad) * Math.cos(refLatRad);

  // Y = R * deltaLat
  const y = EARTH_RADIUS * (latRad - refLatRad);

  return { x, y };
};
