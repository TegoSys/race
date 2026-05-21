# Lessons Learned: Race Track Plot Implementation

## Problem: Maximum Call Stack Size Exceeded
During the implementation of the Race Track Plot, the application encountered a `Maximum call stack size exceeded` error. This prevented the plot from rendering and crashed the browser tab.

## Root Causes

### 1. Spread Operator on Large Arrays
The initial implementation used `Math.min(...array)` and `Math.max(...array)` to calculate the bounding box of the GPS coordinates. 
- **Why it failed**: In JavaScript, the spread operator pushes all array elements onto the stack as function arguments. For large telemetry files (thousands of points), this exceeds the stack limit.

### 2. SVG Rendering Overhead
Attempting to render the track path with `downsample_factor: 1` (full resolution) caused the browser to struggle.
- **Why it failed**: Recharts renders the `Scatter` chart as an SVG. Creating a single SVG path with thousands of segments is computationally expensive and can trigger stack limits during the rendering process.

### 3. CSS Layout Loops (Infinite Resize)
A `ResponsiveContainer` placed inside a `div` with `aspect-ratio: 1/1` and no fixed height created an infinite loop.
- **Why it failed**: The container's height depended on the child, and the child (ResponsiveContainer) attempted to fill the parent's height, triggering continuous resize events.

## Solutions & Best Practices

### 1. Use Explicit Loops for Large Data
Instead of the spread operator, use a standard `for...of` loop or `reduce` to find minimum and maximum values.
- **Correct Approach**:
  ```typescript
  let minX = Infinity, maxX = -Infinity;
  for (const p of data) {
    if (p.x < minX) minX = p.x;
    if (p.x > maxX) maxX = p.x;
  }
  ```

### 2. Implement Strategic Downsampling
For visualizations where every single point is not required (like a track map), use a reasonable downsample factor.
- **Correction**: Changed `downsample_factor` from `1` to `100`. This reduces the number of rendered SVG elements while preserving the overall shape of the track.

**Pro Tip for High-Resolution Maps**: To create a clean, continuous path without the overhead of thousands of individual dot elements (which can cause blurriness and slow performance), use the following `Scatter` configuration:
```tsx
<Scatter
  name="Vehicle Path"
  data={plotState.data}
  fill="#3b82f6"
  fillOpacity={0.4}
  line={{ stroke: "#3b82f6", strokeWidth: 1 }} // Group line props in an object
  shape={() => null} // Hides the individual dots, rendering only the connecting line
/>
```
This approach ensures a crisp line while avoiding the "blob" effect caused by thousands of overlapping points.

### 3. Provide Stable Layout Constraints
When using `ResponsiveContainer`, ensure the parent has a defined height or a fixed dimension to break resize loops.
- **Correction**: Replaced `aspect-square` with a fixed height container (`h-[600px]`) and added `minHeight={0}` to the container.

### 4. Batch State Updates
To reduce re-renders and potential layout thrashing, consolidate multiple related state updates into a single object.
- **Correction**: Combined `data` and `domains` state into a single `plotState` object.
