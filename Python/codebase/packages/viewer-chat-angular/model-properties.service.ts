import { Injectable } from '@angular/core';

export interface PropertyInfo {
  name: string;
  displayName: string;
  category: string;
  sampleValues: string[];
}

export interface ModelMetadata {
  categories: string[];
  properties: PropertyInfo[];
  elementCount: number;
}

/**
 * Service to extract property information from the loaded model.
 * This helps the AI agent understand what properties are available for searching.
 */
@Injectable({
  providedIn: 'root'
})
export class ModelPropertiesService {
  private viewer: any = null;
  private cachedMetadata: ModelMetadata | null = null;

  setViewer(viewer: any): void {
    this.viewer = viewer;
    this.cachedMetadata = null; // Reset cache when viewer changes
  }

  /**
   * Get all available properties from the model.
   * Scans a sample of elements to discover property names.
   */
  async getModelMetadata(): Promise<ModelMetadata> {
    if (this.cachedMetadata) {
      return this.cachedMetadata;
    }

    if (!this.viewer?.model) {
      return { categories: [], properties: [], elementCount: 0 };
    }

    const metadata: ModelMetadata = {
      categories: [],
      properties: [],
      elementCount: 0
    };

    try {
      // Get all dbIds in the model
      const instanceTree = this.viewer.model.getInstanceTree();
      if (!instanceTree) {
        return metadata;
      }

      const allDbIds: number[] = [];
      instanceTree.enumNodeChildren(instanceTree.getRootId(), (dbId: number) => {
        allDbIds.push(dbId);
      }, true);

      metadata.elementCount = allDbIds.length;

      // Sample elements to discover properties (limit to avoid performance issues)
      const sampleSize = Math.min(50, allDbIds.length);
      const sampleIds = this.getRandomSample(allDbIds, sampleSize);

      const propertyMap = new Map<string, PropertyInfo>();
      const categorySet = new Set<string>();

      // Get properties from sample elements
      for (const dbId of sampleIds) {
        const props = await this.getElementProperties(dbId);
        if (props) {
          // Track categories
          const category = props.properties?.find((p: any) =>
            p.displayName === 'Category' || p.attributeName === 'Category'
          );
          if (category?.displayValue) {
            categorySet.add(category.displayValue);
          }

          // Track all properties
          for (const prop of props.properties || []) {
            const key = prop.displayName || prop.attributeName;
            if (!key) continue;

            if (!propertyMap.has(key)) {
              propertyMap.set(key, {
                name: prop.attributeName || key,
                displayName: prop.displayName || key,
                category: prop.displayCategory || 'General',
                sampleValues: []
              });
            }

            // Add sample value
            const propInfo = propertyMap.get(key)!;
            if (prop.displayValue &&
                propInfo.sampleValues.length < 5 &&
                !propInfo.sampleValues.includes(prop.displayValue)) {
              propInfo.sampleValues.push(prop.displayValue);
            }
          }
        }
      }

      metadata.categories = Array.from(categorySet).sort();
      metadata.properties = Array.from(propertyMap.values());

      // Cache the result
      this.cachedMetadata = metadata;

      return metadata;
    } catch (error) {
      console.error('Error getting model metadata:', error);
      return metadata;
    }
  }

  /**
   * Get properties commonly used for searching/filtering
   */
  async getSearchableProperties(): Promise<string[]> {
    const metadata = await this.getModelMetadata();

    // Common property names that are useful for searching
    const commonSearchProps = [
      'Category', 'Type', 'Family', 'Level', 'Material', 'Material Type',
      'Name', 'Mark', 'Type Name', 'System Type', 'Phase Created',
      'Structural Material', 'Assembly Code', 'Type Mark'
    ];

    // Find which ones exist in this model
    const availableProps = metadata.properties
      .filter(p => commonSearchProps.some(cp =>
        p.displayName.toLowerCase().includes(cp.toLowerCase()) ||
        p.name.toLowerCase().includes(cp.toLowerCase())
      ))
      .map(p => p.displayName);

    return [...new Set(availableProps)];
  }

  /**
   * Find the correct property name for a search term.
   * E.g., if user says "material", find if model has "Material", "Material Type", etc.
   */
  async findMatchingProperty(searchTerm: string): Promise<string | null> {
    const metadata = await this.getModelMetadata();
    const termLower = searchTerm.toLowerCase();

    // Exact match first
    const exact = metadata.properties.find(p =>
      p.displayName.toLowerCase() === termLower ||
      p.name.toLowerCase() === termLower
    );
    if (exact) return exact.displayName;

    // Partial match
    const partial = metadata.properties.find(p =>
      p.displayName.toLowerCase().includes(termLower) ||
      p.name.toLowerCase().includes(termLower)
    );
    if (partial) return partial.displayName;

    return null;
  }

  /**
   * Get all unique values for a specific property
   */
  async getPropertyValues(propertyName: string, limit: number = 100): Promise<string[]> {
    if (!this.viewer?.model) return [];

    const values = new Set<string>();

    try {
      const instanceTree = this.viewer.model.getInstanceTree();
      if (!instanceTree) return [];

      const allDbIds: number[] = [];
      instanceTree.enumNodeChildren(instanceTree.getRootId(), (dbId: number) => {
        allDbIds.push(dbId);
      }, true);

      // Sample to avoid performance issues
      const sampleSize = Math.min(200, allDbIds.length);
      const sampleIds = this.getRandomSample(allDbIds, sampleSize);

      for (const dbId of sampleIds) {
        if (values.size >= limit) break;

        const props = await this.getElementProperties(dbId);
        const prop = props?.properties?.find((p: any) =>
          p.displayName === propertyName || p.attributeName === propertyName
        );

        if (prop?.displayValue) {
          values.add(prop.displayValue);
        }
      }

      return Array.from(values).sort();
    } catch (error) {
      console.error('Error getting property values:', error);
      return [];
    }
  }

  /**
   * Get summary for chat context
   */
  async getModelSummaryForChat(): Promise<string> {
    const metadata = await this.getModelMetadata();
    const searchableProps = await this.getSearchableProperties();

    let summary = `Model has ${metadata.elementCount} elements.\n`;

    if (metadata.categories.length > 0) {
      summary += `Categories: ${metadata.categories.join(', ')}\n`;
    }

    if (searchableProps.length > 0) {
      summary += `Searchable properties: ${searchableProps.join(', ')}`;
    }

    return summary;
  }

  // ============= PRIVATE METHODS =============

  private getElementProperties(dbId: number): Promise<any> {
    return new Promise((resolve) => {
      this.viewer.getProperties(dbId, resolve, () => resolve(null));
    });
  }

  private getRandomSample<T>(array: T[], size: number): T[] {
    const shuffled = [...array].sort(() => 0.5 - Math.random());
    return shuffled.slice(0, size);
  }

  /**
   * Clear cached metadata (call when model changes)
   */
  clearCache(): void {
    this.cachedMetadata = null;
  }
}
