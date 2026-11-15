/** The address of an image file inside the site's own data folder. Absolute addresses (for example from the API)
 *  are reduced to the file name, so images never come from another host. */
export function dataFileUrl(base: string, name: string): string {
  return `${base}/${name.split('/').pop()}`;
}
