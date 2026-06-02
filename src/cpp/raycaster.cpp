// Orx C++ Ray-Caster: DDA algorithm optimized for performance.
// Compiled as a Python extension via pybind11.

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <vector>
#include <cmath>
#include <tuple>

namespace py = pybind11;

struct RayHit {
    float distance;
    int wall_type;
    int side;
    float tex_x;
    float hit_x;
    float hit_y;
};

class WorldGrid {
public:
    std::vector<int> grid;
    int width;
    int height;

    WorldGrid(const std::vector<std::vector<int>>& g) {
        height = g.size();
        width = height > 0 ? g[0].size() : 0;
        grid.resize(width * height);
        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                grid[y * width + x] = g[y][x];
            }
        }
    }

    bool is_wall(int x, int y) const {
        if (x < 0 || x >= width || y < 0 || y >= height) return true;
        return grid[y * width + x] != 0;
    }

    int get_tile(int x, int y) const {
        if (x < 0 || x >= width || y < 0 || y >= height) return 1;
        return grid[y * width + x];
    }
};

RayHit cast_single_ray(float px, float py, float angle, const WorldGrid& world, float max_depth) {
    float sin_a = std::sin(angle);
    float cos_a = std::cos(angle);

    float dx = cos_a;
    float dy = sin_a;

    int map_x = static_cast<int>(px);
    int map_y = static_cast<int>(py);

    float delta_dist_x, delta_dist_y;
    int step_x, step_y;

    if (dx == 0.0f) {
        delta_dist_x = 1e30f;
        step_x = 0;
    } else if (dx > 0) {
        delta_dist_x = 1.0f / dx;
        step_x = 1;
    } else {
        delta_dist_x = -1.0f / dx;
        step_x = -1;
    }

    if (dy == 0.0f) {
        delta_dist_y = 1e30f;
        step_y = 0;
    } else if (dy > 0) {
        delta_dist_y = 1.0f / dy;
        step_y = 1;
    } else {
        delta_dist_y = -1.0f / dy;
        step_y = -1;
    }

    float side_dist_x = (dx > 0) ? (map_x + 1 - px) * delta_dist_x : (px - map_x) * delta_dist_x;
    float side_dist_y = (dy > 0) ? (map_y + 1 - py) * delta_dist_y : (py - map_y) * delta_dist_y;

    int side = 0;
    int max_steps = static_cast<int>(max_depth * 2);

    for (int i = 0; i < max_steps; i++) {
        if (side_dist_x < side_dist_y) {
            side_dist_x += delta_dist_x;
            map_x += step_x;
            side = 0;
        } else {
            side_dist_y += delta_dist_y;
            map_y += step_y;
            side = 1;
        }

        if (world.is_wall(map_x, map_y)) {
            float perp_dist;
            float hit_x;
            float tex_x;

            if (side == 0) {
                perp_dist = (dx != 0) ? (map_x - px + (1 - step_x) / 2.0f) / dx : max_depth;
                hit_x = py + perp_dist * dy;
                tex_x = hit_x - std::floor(hit_x);
            } else {
                perp_dist = (dy != 0) ? (map_y - py + (1 - step_y) / 2.0f) / dy : max_depth;
                hit_x = px + perp_dist * dx;
                tex_x = hit_x - std::floor(hit_x);
            }

            tex_x = tex_x - std::floor(tex_x);
            int wall_type = world.get_tile(map_x, map_y);

            RayHit hit;
            hit.distance = perp_dist;
            hit.wall_type = wall_type;
            hit.side = side;
            hit.tex_x = tex_x;
            hit.hit_x = map_x + 0.5f;
            hit.hit_y = map_y + 0.5f;
            return hit;
        }
    }

    RayHit miss;
    miss.distance = max_depth;
    miss.wall_type = 0;
    miss.side = 0;
    miss.tex_x = 0.0f;
    miss.hit_x = 0.0f;
    miss.hit_y = 0.0f;
    return miss;
}

std::vector<std::tuple<float, int, int, float>> cast_rays(
    float px, float py, float player_angle,
    const std::vector<std::vector<int>>& grid,
    float fov, int num_rays, float max_depth) {

    WorldGrid world(grid);
    std::vector<std::tuple<float, int, int, float>> results;
    results.reserve(num_rays);

    float fov_rad = fov * M_PI / 180.0f;
    float half_fov = fov_rad / 2.0f;
    float angle_step = fov_rad / num_rays;

    for (int i = 0; i < num_rays; i++) {
        float ray_angle = player_angle - half_fov + i * angle_step;
        RayHit hit = cast_single_ray(px, py, ray_angle, world, max_depth);
        results.push_back(std::make_tuple(hit.distance, hit.wall_type, hit.side, hit.tex_x));
    }

    return results;
}

bool resolve_collision(
    float& x, float& y, float dx, float dy, float radius,
    const std::vector<std::vector<int>>& grid) {

    WorldGrid world(grid);

    float new_x = x + dx;
    bool x_ok = true;
    if (world.is_wall(static_cast<int>(new_x + radius), static_cast<int>(y + radius)) ||
        world.is_wall(static_cast<int>(new_x - radius), static_cast<int>(y + radius)) ||
        world.is_wall(static_cast<int>(new_x + radius), static_cast<int>(y - radius)) ||
        world.is_wall(static_cast<int>(new_x - radius), static_cast<int>(y - radius))) {
        x_ok = false;
    }

    float new_y = y + dy;
    bool y_ok = true;
    if (world.is_wall(static_cast<int>((x_ok ? new_x : x) + radius), static_cast<int>(new_y + radius)) ||
        world.is_wall(static_cast<int>((x_ok ? new_x : x) - radius), static_cast<int>(new_y + radius)) ||
        world.is_wall(static_cast<int>((x_ok ? new_x : x) + radius), static_cast<int>(new_y - radius)) ||
        world.is_wall(static_cast<int>((x_ok ? new_x : x) - radius), static_cast<int>(new_y - radius))) {
        y_ok = false;
    }

    if (x_ok) x = new_x;
    if (y_ok) y = new_y;

    return x_ok || y_ok;
}

PYBIND11_MODULE(orx_cpp, m) {
    m.doc() = "Orx C++ ray-caster and collision extensions";

    m.def("cast_rays", &cast_rays,
          "Cast all rays and return list of (distance, wall_type, side, tex_x)",
          py::arg("px"), py::arg("py"), py::arg("player_angle"),
          py::arg("grid"), py::arg("fov"), py::arg("num_rays"), py::arg("max_depth"));

    m.def("resolve_collision", &resolve_collision,
          "Resolve player collision with wall grid",
          py::arg("x"), py::arg("y"), py::arg("dx"), py::arg("dy"),
          py::arg("radius"), py::arg("grid"));
}
