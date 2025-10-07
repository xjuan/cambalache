/*
 * Copyright (C) 2021-2024 Juan Pablo Ugarte.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; version 2 of the License.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
 *
 * Authors:
 *   Juan Pablo Ugarte <juanpablougarte@gmail.com>
 */

#include <cmb_catalog_utils.h>


/**
 * cmb_catalog_utils_implements_buildable_add_child:
 * @buildable: Object to check
 *
 * Return whether buildable implements add_child() or not
 *
 */
gboolean
cmb_catalog_utils_implements_buildable_add_child(GObject *buildable)
{
  GtkBuildableIface *iface = NULL;

  if (!GTK_IS_BUILDABLE(buildable))
    return FALSE;

  iface = GTK_BUILDABLE_GET_IFACE(buildable);
  while (iface)
    {
      if (iface->add_child != NULL)
        return TRUE;

      iface = g_type_interface_peek_parent(iface);
    }

  return FALSE;
}

/**
 * cmb_catalog_utils_buildable_get_internal_child:
 * @buildable: Object to check
 * @childname: internal child
 *
 * Return internal child
 *
 * Returns: (transfer none): the internal child of the buildable object
 */
GObject *
cmb_catalog_utils_buildable_get_internal_child(GtkBuildable *buildable,
                                               const char   *childname)
{
  GtkBuilder *builder = NULL;
  GtkBuildableIface *iface;
  GObject *retval = NULL;

  g_return_val_if_fail (GTK_IS_BUILDABLE (buildable), NULL);
  g_return_val_if_fail (childname != NULL, NULL);

  iface = GTK_BUILDABLE_GET_IFACE (buildable);
  if (!iface->get_internal_child)
    return NULL;

  builder = gtk_builder_new ();
  retval = (* iface->get_internal_child) (buildable, builder, childname);
  g_object_unref(builder);

  return retval;
}

#if GTK_MAJOR_VERSION == 3

/**
 * cmb_catalog_utils_a11y_action_get_name:
 * @accessible:
 *
 *
 */
gchar *
cmb_catalog_utils_a11y_action_get_name(AtkObject *accessible)
{
  if (ATK_IS_ACTION (accessible))
    {
      AtkAction *action = ATK_ACTION (accessible);
      gint n_actions = atk_action_get_n_actions (action);

      if (n_actions == 0)
        return NULL;

      GString *retval = g_string_new("");

      for (gint i = 0; i < n_actions; i++)
        {
          g_string_append(retval, atk_action_get_name (action, i));
          if (i < (n_actions-1)) g_string_append(retval, "\n");
        }
      return g_string_free_and_steal(retval);
    }

  return NULL;
}
#endif
