import { create } from 'zustand';

export const useLiveStore = create((set) => ({
    // Mảng chứa các điểm dữ liệu (tối đa 20 điểm để chart không bị tràn)
    livePoints: [],
    liveData: [],
    latestLiveData: null,

    // Hàm thêm dữ liệu mới từ WebSocket
    addPoint: (newData) => set((state) => {
        const timestamp = newData.timestamp ?? new Date().toISOString();
        const dataPoint = {
            ...newData,
            predicted_load: newData.predicted_load != null ? Number(newData.predicted_load) : null,
            simulated_temp: newData.simulated_temp != null ? Number(newData.simulated_temp) : null,
            timestamp,
            time: newData.time ?? new Date(timestamp).toLocaleTimeString('vi-VN')
        };

        const updatedData = [...state.livePoints, dataPoint].slice(-20);
        return { livePoints: updatedData, liveData: updatedData, latestLiveData: dataPoint };
    }),
    addLiveData: (newData) => set((state) => {
        const timestamp = newData.timestamp ?? new Date().toISOString();
        const dataPoint = {
            ...newData,
            predicted_load: newData.predicted_load != null ? Number(newData.predicted_load) : null,
            simulated_temp: newData.simulated_temp != null ? Number(newData.simulated_temp) : null,
            timestamp,
            time: newData.time ?? new Date(timestamp).toLocaleTimeString('vi-VN')
        };

        const updatedData = [...state.livePoints, dataPoint].slice(-20);
        return { livePoints: updatedData, liveData: updatedData, latestLiveData: dataPoint };
    }),

    // Trạng thái kết nối (để hiển thị icon online/offline)
    isConnected: false,
    setConnected: (status) => set({ isConnected: status }),

    isDemoMode: false,
    setDemoMode: (status) => set({ isDemoMode: status }),

    resetLiveData: () => set({
        livePoints: [],
        liveData: [],
        latestLiveData: null,
        isConnected: false,
        isDemoMode: false
    })
}));
