'use client';

import React, { useState } from 'react';
import { Plus, DoorOpen, Users, FlaskConical, Dumbbell, Monitor, Trash2 } from 'lucide-react';
import { useSchoolData } from '@/context/SchoolDataContext';

export type RoomType = 'GENERAL' | 'LABORATORY' | 'GYM' | 'COMPUTER_LAB';

export interface RoomItem {
  id: string;
  roomNumber: string;
  name: string;
  capacity: number;
  roomType: RoomType;
}

export const RoomsModule: React.FC = () => {
  const { rooms, addRoom, deleteRoom } = useSchoolData();
  const [showModal, setShowModal] = useState(false);

  // Form states
  const [roomNumber, setRoomNumber] = useState('');
  const [name, setName] = useState('');
  const [capacity, setCapacity] = useState(30);
  const [roomType, setRoomType] = useState<RoomType>('GENERAL');

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!roomNumber) return;

    const newR: RoomItem = {
      id: `r_${Date.now()}`,
      roomNumber,
      name: name || roomNumber,
      capacity: Number(capacity),
      roomType,
    };

    addRoom(newR);
    setShowModal(false);
    setRoomNumber('');
    setName('');
  };

  const handleDelete = (id: string) => {
    if (confirm("Xonani o'chirmoqchimisiz?")) {
      deleteRoom(id);
    }
  };

  const getBadge = (type: RoomType) => {
    switch (type) {
      case 'LABORATORY':
        return { label: 'Laboratoriya', color: 'bg-purple-100 text-purple-700', icon: FlaskConical };
      case 'GYM':
        return { label: 'Sport Zal', color: 'bg-amber-100 text-amber-700', icon: Dumbbell };
      case 'COMPUTER_LAB':
        return { label: 'Kompyuter', color: 'bg-cyan-100 text-cyan-700', icon: Monitor };
      default:
        return { label: 'Oddiy xona', color: 'bg-gray-100 text-gray-700', icon: DoorOpen };
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-[#FFFFFF] p-5 rounded-2xl border border-gray-200 shadow-sm flex items-center justify-between">
        <div>
          <h3 className="font-bold text-gray-900 text-lg">Maktab Xonalari & Sig'imi</h3>
          <p className="text-xs text-gray-500">
            Jami <span className="font-bold text-gray-900">{rooms.length} ta xona</span> mavjud ({rooms.filter(r => r.roomType === 'LABORATORY').length} ta Laboratoriya, {rooms.filter(r => r.roomType === 'GYM').length} ta Sport zal)
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 bg-[#10B981] hover:bg-emerald-600 text-white font-medium text-sm px-5 py-2.5 rounded-xl shadow-sm transition active:scale-95"
        >
          <Plus className="w-4 h-4" />
          <span>Yangi Xona Qo'shish</span>
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {rooms.map((room) => {
          const badge = getBadge(room.roomType);
          const BadgeIcon = badge.icon;
          return (
            <div
              key={room.id}
              className="bg-[#FFFFFF] p-5 rounded-2xl border border-gray-200/80 shadow-sm hover:shadow-md transition relative group"
            >
              <div className="flex items-start justify-between">
                <div>
                  <span
                    className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold ${badge.color}`}
                  >
                    <BadgeIcon className="w-3 h-3" />
                    {badge.label}
                  </span>
                  <h4 className="font-extrabold text-gray-900 text-lg mt-2">{room.roomNumber}</h4>
                  <div className="text-xs text-gray-500">{room.name}</div>
                </div>

                <button
                  onClick={() => handleDelete(room.id)}
                  className="opacity-0 group-hover:opacity-100 p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-600">
                <div className="flex items-center gap-1.5 font-medium">
                  <Users className="w-3.5 h-3.5 text-gray-400" />
                  <span>Maksimal: {room.capacity} o'quvchi</span>
                </div>
                <span className="text-[#10B981] font-semibold">Mos va bo'sh</span>
              </div>
            </div>
          );
        })}
      </div>

      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#FFFFFF] rounded-2xl max-w-md w-full p-6 shadow-2xl border border-gray-100">
            <h3 className="text-lg font-bold text-[#1E40AF] mb-4">Yangi Xona Qo'shish</h3>
            <form onSubmit={handleAdd} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-gray-700 block mb-1">Xona Raqami / Nomi:</label>
                <input
                  type="text"
                  required
                  placeholder="Masalan: 204-xona yoki Kimyo Lab"
                  value={roomNumber}
                  onChange={(e) => setRoomNumber(e.target.value)}
                  className="w-full px-3.5 py-2 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-gray-700 block mb-1">Qo'shimcha izoh / Tavsif:</label>
                <input
                  type="text"
                  placeholder="Masalan: 2-qavat chap qanot"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3.5 py-2 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-gray-700 block mb-1">Sig'imi (o'quvchi):</label>
                  <input
                    type="number"
                    min="10"
                    max="100"
                    value={capacity}
                    onChange={(e) => setCapacity(Number(e.target.value))}
                    className="w-full px-3.5 py-2 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-gray-700 block mb-1">Xona turi:</label>
                  <select
                    value={roomType}
                    onChange={(e) => setRoomType(e.target.value as any)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-[#1E40AF] outline-none bg-white"
                  >
                    <option value="GENERAL">Oddiy sinf xonasi</option>
                    <option value="LABORATORY">Laboratoriya</option>
                    <option value="GYM">Sport zal</option>
                    <option value="COMPUTER_LAB">Kompyuter / IT</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-xl transition"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-sm bg-[#10B981] hover:bg-emerald-600 text-white font-medium rounded-xl shadow transition"
                >
                  Saqlash
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
